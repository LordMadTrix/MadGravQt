"""
Webhelp is a list of websites relevant to the program. This registers a `webhelp` command that will launch a browser
point to the relvant sites.
"""

MADGRAV_ISSUES = "https://github.com/madgrav/madgrav/issues"
MADGRAV_HELP = "https://github.com/madgrav/madgrav/wiki"
MADGRAV_BEGINNERS = "https://github.com/madgrav/madgrav/wiki/Beginners:-0.-Index"
MADGRAV_WEBSITE = "https://github.com/madgrav/madgrav"
MADGRAV_RELEASES = "https://github.com/madgrav/madgrav/releases"
FACEBOOK_MADGRAV = "https://www.facebook.com/groups/716000085655097"
DISCORD_MADGRAV = "https://discord.gg/vkDD3HdQq6"
MAKERS_FORUM_MADGRAV = "https://forum.makerforums.info/c/k40/madgrav/120"
# IRC_CLIENT = "http://kiwiirc.com/client/irc.libera.chat/madgrav"
MADGRAV_FEATURE = "https://github.com/madgrav/madgrav/discussions/new/choose"


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

        @kernel.console_argument("page", help=_("Webhelp page"), type=str)
        @kernel.console_command("webhelp", help=_("Launch a registered webhelp page"))
        def webhelp(channel, _, page=None, **kwargs):
            if page is None:
                channel(_("----------"))
                channel(_("Webhelp Registered:"))
                for i, find in enumerate(kernel.find("webhelp")):
                    value, name, suffix = find
                    channel(f"{i + 1}: {str(suffix).ljust(15)} {value}")
                channel(_("----------"))
                return
            try:
                page_num = int(page)
                for i, find in enumerate(kernel.find("webhelp")):
                    if i == page_num:
                        value, name, suffix = find
                        page = value
            except ValueError:
                pass
            value = kernel.lookup("webhelp", page)
            if value is None:
                channel(_("Webhelp not found."))
                return
            value = str(value)
            if not value.startswith("http"):
                channel("bad webhelp")
                return
            import webbrowser

            webbrowser.open(value, new=0, autoraise=True)

        kernel.register("webhelp/help", MADGRAV_HELP)
        kernel.register("webhelp/beginners", MADGRAV_BEGINNERS)
        kernel.register("webhelp/main", MADGRAV_WEBSITE)
        kernel.register("webhelp/issues", MADGRAV_ISSUES)
        kernel.register("webhelp/releases", MADGRAV_RELEASES)
        kernel.register("webhelp/facebook", FACEBOOK_MADGRAV)
        kernel.register("webhelp/discord", DISCORD_MADGRAV)
        kernel.register("webhelp/makers", MAKERS_FORUM_MADGRAV)
        # kernel.register("webhelp/irc", IRC_CLIENT)
        kernel.register("webhelp/featurerequest", MADGRAV_FEATURE)
