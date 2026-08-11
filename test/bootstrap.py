from madgrav.kernel import Kernel


def bootstrap(profile="MadGrav_TEST", ignore_settings=True, plugins=None):
    kernel = Kernel(
        "MadGrav",
        "0.0.0-testing",
        profile,
        ansi=False,
        ignore_settings=ignore_settings,
    )

    from madgrav.network import kernelserver

    kernel.add_plugin(kernelserver.plugin)

    from madgrav.device import dummydevice

    kernel.add_plugin(dummydevice.plugin)

    from madgrav.core import core

    kernel.add_plugin(core.plugin)

    from madgrav.image import imagetools

    kernel.add_plugin(imagetools.plugin)

    from madgrav.fill import fills

    kernel.add_plugin(fills.plugin)

    from madgrav.extra.coolant import plugin as coolantplugin

    kernel.add_plugin(coolantplugin)

    from madgrav.lihuiyu import plugin as lhystudiosdevice

    kernel.add_plugin(lhystudiosdevice.plugin)

    from madgrav.moshi import plugin as moshidevice

    kernel.add_plugin(moshidevice.plugin)

    from madgrav.grbl import plugin as grbldevice

    kernel.add_plugin(grbldevice.plugin)

    from madgrav.ruida import plugin as ruidadevice

    kernel.add_plugin(ruidadevice.plugin)

    from madgrav.newly import plugin as newlydevice

    kernel.add_plugin(newlydevice.plugin)

    from madgrav.balormk import plugin as balormkdevice

    kernel.add_plugin(balormkdevice.plugin)

    from madgrav.core import svg_io

    kernel.add_plugin(svg_io.plugin)

    from madgrav.dxf.plugin import plugin as dxf_io_plugin

    kernel.add_plugin(dxf_io_plugin)

    from madgrav.rotary import rotary

    kernel.add_plugin(rotary.plugin)

    if plugins:
        for plugin in plugins:
            kernel.add_plugin(plugin)

    kernel(partial=True)
    kernel.console("channel print console\n")
    kernel.console("service device start dummy 0\n")
    return kernel


def destroy(kernel):
    for i in range(50):
        kernel.console(f"service device destroy {i}\n")
