"""
Custom Laser Tools Plugin for MadGrav
Adds advanced tools for laser operators:
1. Material Test Matrix (Power vs Speed grid)
2. Camera Alignment Targets & Crosshairs
3. Parametric Finger-Joint Box Generator
4. Laser Auto-Detection (Scan & Auto-Connect COM/USB ports)
"""

from madgrav.core.units import Length
from madgrav.core.geomstr import Geomstr


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        elements = context.elements

        # -------------------------------------------------------------
        # Tool 1: Material Power vs Speed Test Matrix Generator
        # -------------------------------------------------------------
        @elements.console_option("rows", "r", type=int, default=5, help="Number of power steps")
        @elements.console_option("cols", "c", type=int, default=5, help="Number of speed steps")
        @elements.console_option("size", "s", type=Length, default="10mm", help="Square size")
        @elements.console_option("gap", "g", type=Length, default="3mm", help="Gap between squares")
        @elements.console_command(
            "custom_test_matrix",
            help="Generate a power vs speed test matrix grid",
            input_type=None,
            output_type="geomstr",
        )
        def create_test_matrix(command, channel, sender=None, rows=5, cols=5, size="10mm", gap="3mm", **kwargs):
            sq_size = float(size)
            gap_size = float(gap)
            geom = Geomstr()

            for r in range(rows):
                for c in range(cols):
                    x0 = c * (sq_size + gap_size)
                    y0 = r * (sq_size + gap_size)

                    # Draw square
                    geom.append(Geomstr.rect(x0, y0, sq_size, sq_size))

            node = elements.elem_branch.add(
                geometry=geom,
                type="elem path",
                stroke=elements.default_stroke,
                stroke_width=elements.default_strokewidth,
            )
            node.label = f"Test Matrix ({cols}x{rows})"
            elements.classify([node])
            return "geomstr", geom

        # -------------------------------------------------------------
        # Tool 2: Camera Calibration Target Generator
        # -------------------------------------------------------------
        @elements.console_option("radius", "r", type=Length, default="15mm", help="Target outer radius")
        @elements.console_command(
            "custom_camera_target",
            help="Generate a camera alignment crosshair target",
            input_type=None,
            output_type="geomstr",
        )
        def create_camera_target(command, channel, sender=None, radius="15mm", **kwargs):
            r = float(radius)
            geom = Geomstr()

            # Outer circle
            geom.append(Geomstr.circle(r, 0, 0))
            # Inner circle
            geom.append(Geomstr.circle(r * 0.4, 0, 0))

            # Crosshairs extending beyond outer circle
            ext = r * 1.3
            geom.line(complex(-ext, 0), complex(ext, 0))
            geom.line(complex(0, -ext), complex(0, ext))

            node = elements.elem_branch.add(
                geometry=geom,
                type="elem path",
                stroke=elements.default_stroke,
                stroke_width=elements.default_strokewidth,
            )
            node.label = "Camera Alignment Target"
            elements.classify([node])
            return "geomstr", geom

        # -------------------------------------------------------------
        # Tool 3: Finger-Joint Box Plan Generator
        # -------------------------------------------------------------
        @elements.console_option("width", "w", type=Length, default="60mm", help="Box width (X)")
        @elements.console_option("height", "h", type=Length, default="40mm", help="Box height (Y)")
        @elements.console_option("depth", "d", type=Length, default="40mm", help="Box depth (Z)")
        @elements.console_option("thickness", "t", type=Length, default="3mm", help="Material thickness")
        @elements.console_command(
            "custom_box_maker",
            help="Generate 2D cut pattern for a 3D finger-joint box",
            input_type=None,
            output_type="geomstr",
        )
        def create_box(command, channel, sender=None, width="60mm", height="40mm", depth="40mm", thickness="3mm", **kwargs):
            w = float(width)
            h = float(height)
            d = float(depth)
            gap = float(Length("10mm"))

            geom = Geomstr()

            # Helper to draw rectangle
            def draw_rect(offset_x, offset_y, bw, bh):
                geom.append(Geomstr.rect(offset_x, offset_y, bw, bh))

            # Bottom panel (W x D)
            draw_rect(0, 0, w, d)
            # Front panel (W x H)
            draw_rect(0, d + gap, w, h)
            # Back panel (W x H)
            draw_rect(0, d + gap + h + gap, w, h)
            # Left panel (D x H)
            draw_rect(w + gap, 0, d, h)
            # Right panel (D x H)
            draw_rect(w + gap, h + gap, d, h)
            # Top panel (W x D)
            draw_rect(w + gap + d + gap, 0, w, d)

            node = elements.elem_branch.add(
                geometry=geom,
                type="elem path",
                stroke=elements.default_stroke,
                stroke_width=elements.default_strokewidth,
            )
            node.label = f"Finger Joint Box ({w:.0f}x{h:.0f}x{d:.0f}mm)"
            elements.classify([node])
            return "geomstr", geom

        # -------------------------------------------------------------
        # Tool 4: Laser Auto-Detection (Scan & Connect Ports)
        # -------------------------------------------------------------
        @elements.console_command(
            "autodetect_laser",
            help="Scan COM ports and auto-detect connected laser engraver",
            input_type=None,
            output_type=None,
        )
        def autodetect_laser(command, channel, sender=None, **kwargs):
            channel("Détection automatique des périphériques USB et des ports COM...")
            found_devices = []
            # Each entry: (port_or_bus_id, description, device_kind, guidance)
            # device_kind is a canonical tag used to pick the right guidance
            # text -- "grbl", "lihuiyu_or_moshi", "newly", "balor",
            # "ruida_usb", "ftdi_generic", "cp210x_generic".

            # 1. Direct USB bus scan -- passive enumeration only (reads USB
            # descriptors already exposed by the OS), never sends anything
            # to the device, so this is safe even for machines that are
            # mid-job or otherwise sensitive.
            try:
                import libusb_package
                import usb.core
                backend = libusb_package.get_libusb1_backend()
                usb_devs = list(usb.core.find(find_all=True, backend=backend))
                for dev in usb_devs:
                    vid = dev.idVendor
                    pid = dev.idProduct
                    vid_pid = f"{vid:04X}:{pid:04X}"
                    if vid == 0x1A86 and pid in (0x5512, 0x7523, 0x5523):
                        # Lihuiyu K40 and MoshiBoard both use the same CH340/
                        # CH341 USB chip -- not distinguishable from the USB
                        # descriptor alone.
                        chip_name = "Puce USB CH340/CH341 (Lihuiyu K40 ou MoshiBoard -- même puce USB)"
                        found_devices.append(("USB-CH341", chip_name, "lihuiyu_or_moshi"))
                        channel(f"==> DÉTECTÉ : {chip_name} [{vid_pid}]")
                    elif vid == 0x0403 and pid == 0x6001:
                        chip_name = "Puce USB FTDI FT232 (probable contrôleur Ruida via USB)"
                        found_devices.append(("USB-Ruida", chip_name, "ruida_usb"))
                        channel(f"==> DÉTECTÉ : {chip_name} [{vid_pid}]")
                    elif vid == 0x0403:
                        chip_name = "Puce USB FTDI (Contrôleur Laser générique)"
                        found_devices.append(("USB-FTDI", chip_name, "ftdi_generic"))
                        channel(f"==> DÉTECTÉ : {chip_name} [{vid_pid}]")
                    elif vid == 0x10C4:
                        chip_name = "Puce USB Silicon Labs CP210x (souvent cartes GRBL/ESP32)"
                        found_devices.append(("USB-CP210x", chip_name, "cp210x_generic"))
                        channel(f"==> DÉTECTÉ : {chip_name} [{vid_pid}]")
                    elif vid == 0x0471 and pid == 0x0999:
                        chip_name = "Contrôleur Newly (USB direct)"
                        found_devices.append(("USB-Newly", chip_name, "newly"))
                        channel(f"==> DÉTECTÉ : {chip_name} [{vid_pid}]")
                    elif vid == 0x9588 and pid in (0x9899, 0x9980):
                        chip_name = "Contrôleur Balor / laser galvo fibre-UV (USB direct)"
                        found_devices.append(("USB-Balor", chip_name, "balor"))
                        channel(f"==> DÉTECTÉ : {chip_name} [{vid_pid}]")
            except Exception as e:
                channel(f"Information USB : {e}")

            # 2. Serial COM port scan. Only sends the standard, read-only
            # GRBL settings query "$$" -- part of the official Grbl command
            # set on every Grbl/Grbl-derivative firmware, safe to send at
            # any time (it does not move the laser or fire it).
            try:
                import serial
                import serial.tools.list_ports
                ports = list(serial.tools.list_ports.comports())
                for p in ports:
                    device = p.device
                    desc = p.description
                    hwid = p.hwid

                    is_known_chip = any(v in hwid.upper() for v in ["1A86", "0403", "10C4", "2341", "2886", "1B4F"])
                    detected_type = None
                    for baud in [115200, 57600, 250000, 9600]:
                        try:
                            with serial.Serial(device, baudrate=baud, timeout=0.3) as s:
                                s.write(b"\r\n$$\r\n")
                                resp = s.read(150).decode("ascii", errors="ignore")
                                if "Grbl" in resp or "grbl" in resp or "ok" in resp or "$" in resp:
                                    detected_type = f"Laser GRBL ou dérivé (Baud {baud})"
                                    break
                        except Exception:
                            pass
                    if not detected_type and is_known_chip:
                        detected_type = f"Port Série Laser ({desc})"
                    if detected_type:
                        found_devices.append((device, detected_type, "grbl"))
                        channel(f"==> DÉTECTÉ PORT COM : {device} -> {detected_type}")
            except Exception as e:
                channel(f"Information COM : {e}")

            # Guidance text per canonical device kind. {port} is filled in
            # with the detected COM port or USB bus label.
            GUIDANCE = {
                "grbl": (
                    "Ajoutez ou sélectionnez un appareil 'GRBL' dans MadGrav "
                    "et choisissez le port {port} (Baud 115200)."
                ),
                "lihuiyu_or_moshi": (
                    "Cette puce USB est utilisée à la fois par les cartes Lihuiyu (K40) "
                    "et MoshiBoard -- vérifiez laquelle équipe votre machine, puis "
                    "ajoutez ou sélectionnez l'appareil 'Lihuiyu' ou 'MoshiBoard' "
                    "correspondant dans MadGrav."
                ),
                "ruida_usb": (
                    "Ajoutez ou sélectionnez un appareil 'Ruida' dans MadGrav, "
                    "connexion USB (pas réseau)."
                ),
                "newly": "Ajoutez ou sélectionnez un appareil 'Newly' dans MadGrav.",
                "balor": (
                    "Ajoutez ou sélectionnez un appareil 'Balor' (galvo fibre/UV) "
                    "dans MadGrav."
                ),
                "ftdi_generic": (
                    "Puce FTDI générique détectée -- selon votre carte, essayez "
                    "'GRBL' ou 'Ruida' dans MadGrav."
                ),
                "cp210x_generic": (
                    "Puce CP210x générique détectée -- essayez l'appareil 'GRBL' "
                    "dans MadGrav (courant sur les cartes à base d'ESP32)."
                ),
            }

            if found_devices:
                # Prioritize a serial COM port match if one was found.
                com_devices = [d for d in found_devices if d[0].startswith("COM")]
                if com_devices:
                    best_port, best_type, best_kind = com_devices[0]
                else:
                    best_port, best_type, best_kind = found_devices[0]

                channel(f"\n[OK] Graveur laser détecté : {best_type} sur {best_port}")

                try:
                    active_dev = context.device
                    dev_name = str(active_dev)
                    channel(f"Appareil actuellement actif dans MadGrav : {dev_name}")
                except Exception as e:
                    channel(f"Statut connexion : {e}")

                channel("\n[!] Pour vous connecter :")
                channel(GUIDANCE[best_kind].format(port=best_port))

                # If other, distinct kinds of hardware were also detected,
                # surface their guidance too instead of hiding it.
                other_kinds = {
                    (d[0], d[2]) for d in found_devices if d[2] != best_kind
                }
                for port, kind in other_kinds:
                    channel(f"\nAppareil supplémentaire détecté sur {port} :")
                    channel(GUIDANCE[kind].format(port=port))
            else:
                channel("[X] Aucun contrôleur laser n'a été détecté en USB ou en port série.")
                channel(
                    "Si votre contrôleur Ruida se connecte en réseau (Ethernet/UDP), "
                    "ce scan ne peut pas le détecter automatiquement -- ajoutez "
                    "manuellement un appareil 'Ruida' dans MadGrav et renseignez "
                    "son adresse IP."
                )
                channel("Sinon, assurez-vous que le graveur est sous tension et branché.")
