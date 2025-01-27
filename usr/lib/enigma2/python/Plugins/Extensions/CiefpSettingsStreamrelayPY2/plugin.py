from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, ePicLoad
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Pixmap import Pixmap
from Tools.Directories import fileExists
import os
import re

# Plugin Descriptor
PLUGIN_NAME = "CiefpSettingsStreamrelayPY2"
PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSettingsStreamrelayPY2"
PLUGIN_VERSION = "1.1"
PLUGIN_DESC = "Convert bouquets for StreamRelay."
PLUGIN_ICON = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSettingsStreamrelayPY2/icon.png"
PLUGIN_BG_IMAGE = os.path.join(PLUGIN_DIR, "background.png")


class StreamRelayConverter(Screen):
    skin = """
    <screen name="StreamRelayConverter" position="center,center" size="1200,600" title="Ciefp Settings StreamRelay PY2">
        <widget name="status" position="20,20" size="560,50" font="Regular;25" valign="center" halign="center" />
        <widget name="info" position="20,80" size="560,100" font="Regular;25" valign="center" halign="left" />
        <widget name="menu" position="20,200" size="560,300" scrollbarMode="showOnDemand" />
        <widget name="key_red" position="20,520" size="140,50" font="Bold;18" valign="center" halign="center" backgroundColor="red" foregroundColor="black" />
        <widget name="key_green" position="180,520" size="140,50" font="Bold;18" valign="center" halign="center" backgroundColor="green" foregroundColor="black" />
        <widget name="key_yellow" position="340,520" size="140,50" font="Bold;18" valign="center" halign="center" backgroundColor="yellow" foregroundColor="black" />
        <widget name="key_blue" position="500,520" size="140,50" font="Bold;18" valign="center" halign="center" backgroundColor="blue" foregroundColor="black" />
        <ePixmap pixmap="{0}" position="650,0" size="550,600" alphatest="blend" />
    </screen>
    """.format(PLUGIN_BG_IMAGE)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        self["menu"] = MenuList([("Select Astra 19.2E Bouquet", "19.2E"),
                                 ("Select Astra 28.2E Bouquet", "28.2E")])

        self["status"] = Label("Welcome to Ciefp Settings StreamRelay!")
        self["info"] = Label("Select bouquets to convert.")
        self["key_red"] = Button("Cancel")
        self["key_green"] = Button("Start Conversion")
        self["key_yellow"] = Button("Select Astra 19.2E")
        self["key_blue"] = Button("Select Astra 28.2E")

        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "cancel": self.close,
            "green": self.start_conversion,
            "yellow": self.select_bouquet_19e,
            "blue": self.select_bouquet_28e,
            "red": self.close
        })

        self.selected_bouquets = []

    def select_bouquet_19e(self):
        if "19.2E" not in self.selected_bouquets:
            self.selected_bouquets.append("19.2E")
            self["status"].setText("Selected bouquets: {}".format(", ".join(self.selected_bouquets)))

    def select_bouquet_28e(self):
        if "28.2E" not in self.selected_bouquets:
            self.selected_bouquets.append("28.2E")
            self["status"].setText("Selected bouquets: {}".format(", ".join(self.selected_bouquets)))

    def start_conversion(self):
        if not self.selected_bouquets:
            self["info"].setText("No bouquets selected for conversion.")
            return

        for bouquet in self.selected_bouquets:
            if bouquet == "19.2E":
                self.convert_and_save(
                    bouquet_files=[
                        "userbouquet.ciefp_19e_skydemovies.tv",
                        "userbouquet.ciefp_19e_skydedocu.tv",
                        "userbouquet.ciefp_19e_skydesport.tv"
                    ],
                    output_file="userbouquet.ciefp_19e_skyde_icam.tv",
                    header="#NAME . 19,2 E - Sky DE - icam :: streamrelay ::\n"
                )

            if bouquet == "28.2E":
                self.convert_and_save(
                    bouquet_files=[
                        "userbouquet.ciefp_28e_skyukmovie.tv",
                        "userbouquet.ciefp_28e_skyukdocuments.tv",
                        "userbouquet.ciefp_28e_skyukkids.tv",
                        "userbouquet.ciefp_28e_skyuksports.tv"
                    ],
                    output_file="userbouquet.ciefp_28e_skyuk_icam.tv",
                    header="#NAME . 28,2 E - SKY UK - icam :: streamrelay ::\n"
                )

        self.session.openWithCallback(
            self.confirm_restart,
            MessageBox,
            "Conversion complete.\nDo you want to restart Enigma2?",
            MessageBox.TYPE_YESNO
        )

    def convert_and_save(self, bouquet_files, output_file, header):
        converted_lines = []
        for bouquet_file in bouquet_files:
            bouquet_path = os.path.join("/etc/enigma2", bouquet_file)
            if fileExists(bouquet_path):
                with open(bouquet_path, "r") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines):
                    if line.startswith("#SERVICE 1:64:"):
                        converted_lines.append(line)
                        if i + 1 < len(lines) and lines[i + 1].startswith("#DESCRIPTION"):
                            converted_lines.append(lines[i + 1])
                        continue

                    if line.startswith("#SERVICE"):
                        original_reference = line[len("#SERVICE "):].strip()
                        channel_name = self.get_channel_name_from_reference(original_reference)
                        converted_line = self.process_service_line(line, original_reference, channel_name)
                        converted_lines.append(converted_line)

        output_path = os.path.join("/etc/enigma2", output_file)
        with open(output_path, "w") as f:
            f.write(header)
            f.writelines(converted_lines)

    def get_channel_name_from_reference(self, service_reference):
        parts = service_reference.split(":")
        if len(parts) < 8:
            print("Invalid service reference format: {}".format(service_reference))
            return "Invalid Reference"

        relevant_reference = "{:04x}:{:08x}:{:04x}:{:04x}".format(
            int(parts[3], 16), int(parts[6], 16), int(parts[4], 16), int(parts[5], 16)
        )

        lamedb_path = "/etc/enigma2/lamedb"
        if not fileExists(lamedb_path):
            print("lamedb file not found.")
            return "Unknown Channel"

        try:
            with open(lamedb_path, "r") as f:
                content = f.read()

            entries = content.splitlines()
            for i in range(len(entries) - 2):
                if entries[i].startswith(relevant_reference):
                    channel_name = entries[i + 1].strip()
                    return channel_name

        except Exception as e:
            print("Error reading lamedb: {}".format(e))

        return "Unknown Channel"

    def process_service_line(self, line, original_reference, channel_name):
        parts = line.split(":")
        if len(parts) > 6:
            parts[6] = "21"
        converted_line = ":".join(parts).strip()
        converted_line += "http%3a//127.0.0.1%3a17999/"
        converted_line += original_reference.replace(":", "%3a") + ":"
        converted_line += channel_name
        description_line = "#DESCRIPTION {}".format(channel_name)
        return converted_line + "\n" + description_line + "\n"

    def confirm_restart(self, answer):
        if answer:
            os.system("killall -9 enigma2")


def main(session, **kwargs):
    session.open(StreamRelayConverter)


def Plugins(**kwargs):
    return [PluginDescriptor(
        name="{} v{}".format(PLUGIN_NAME, PLUGIN_VERSION),
        description=PLUGIN_DESC,
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon=PLUGIN_ICON,
        fnc=main
    )]
