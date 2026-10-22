# Patches for EA Nation games
A project dedicated to provide patches to get games to connect to a private server, as well as other features.

## [PSP] Xdelta patches

### Available patches
- **Private Server**
  - **Need For Speed: Most Wanted 5-1-0** : If you want to play using the `EU` version of the game (`ULES00196`), you must patch it so it can connect to the private server using the same port as the US version (by default it overlaps with NFS: Undercover's port).

### Usage

- Download the Xdelta patch of the game matching your .iso version from the `PSP/Xdelta` folder.
- Grab your `.iso` file
- Either go to https://kotcrab.github.io/xdelta-wasm/ (online) or download https://github.com/marco-calautti/DeltaPatcher/releases (software)
- Drop your `.iso` in the first field, drop the XDelta patch in the second, and click `Apply patch`


## [PS2] OPL, pnach & Xdelta patches

### Available patches
- **DNAS bypass** : all patches are made to bypass DNAS checks
  - Check either the `PS2/OPL`, `PS2/pnach` or `PS2/Xdelta` folder for your game.
- **[Tiger Woods PGA Tour 2004 (USA)](doc/TW04.txt)**: PCSX2 and OPL DNAS bypass, leaderboard date fixes, Internet guest address fix, and a configurable private-server patch generator (`--opl` for OPL cheat files). Optional support for the experimental EA Nation relay co-host setup.

### Usage

- **Open PS2 Loader (OPL)**
  - Copy the `.cht` file matching your game's ID from the `PS2/OPL` folder to the `CHT` folder of your FMCB installation.
  - Enable cheats in OPL (Options > Cheats Settings > PS2RD Cheat Engine > ON > Save Changes)

- **Pnach**
  - Copy the `.pnach` file(s) matching your game's ID from the `PS2/pnach` folder to the `cheats` folder of your PCSX2 installation. ⚠️ Beware, some games have multiple pnach files.
  - Enable cheats in PCSX2 settings.

- **Xdelta**
  - Download the Xdelta patch of the game matching your .iso version from the `PS2/Xdelta` folder.
  - Grab your `.iso` file
  - Either go to https://kotcrab.github.io/xdelta-wasm/ (online) or download https://github.com/marco-calautti/DeltaPatcher/releases (software)
  - Drop your `.iso` in the first field, drop the XDelta patch in the second, and click `Apply patch`


## [Wii] Riivolution patches & Gecko Codes

**Riivolution** patches are made for Dolphin only, as the Riivolution homebrew doesn't work with MoHH2 on Wii. **Gecko Codes** is a fallback solution for the Wii.

The patches target the following versions of MoHH2 :
- RM2P69 : PAL UK
- RM2X69 : PAL EU (Fr,De,It,Es)
- RM2E69 : NTSC US
- RM2E69-beta : NTSC US (Oct 17, 2007 prototype)

### Available patches

- **Private Server**
  - **WFC replacement** : Required to access the private server. On Wii you can use the `Private Server` feature of USB Loader GX (recent versions only). Two options supported :
    - NoSSL - Requires to host a [NWC server](https://github.com/a-blondel/nwc-server)
	- Wiimmfi
  - **Serverless** : Allows to start a game alone without a working UDP server. **Beware : it crashes when taking damage !**
- **Mods**
  - **Online Panzerschreck** : Restores the panzerschreck for the germans (which was replaced by the M1 Bazooka on the Wii version while being available on the PSP version)  

<img src="doc/img/panzerschreck-label.png" alt="panzerschreck-label" width="400"/> <img src="doc/img/panzerschreck.png" alt="panzerschreck" width="400"/><br/>
*Panzerschreck label / ingame*
- **Misc**
  - **Menu Theme** : Change the theme menu, optional.
  - **Skip startup screens** : Skips the Wiimote and Wii Zapper alert screens on game startup to spare some time, optional.
  - **Skip EA intro** : Skips the intro to spare some time, optional.


### Usage

- Dolphin
  - Copy and Paste content of the `Wii/Riivolution` folder inside of your `Dolphin/User/Load/Riivolution` folder.
  - Right click on the game, click on `Start with Riivolution Patches`, click on `Open Riivolution XML...` and select the XML related to your version of the game.
  - Activate the patches you need.
- Wii
  - Two options to apply the codes :
    - Copy the .txt file matching your Game ID from the `Wii/GeckoCodes` folder, and paste it in a folder named `txtcodes` at the root of your SD card. Then in your game loader go to `game settings`, `ocarina`, activate the codes you want, and click create. This option is more flexible as you can quickly change the codes on the Wii.
    - Generate a GCT file based on the .txt file matching your Game ID from the `Wii/GeckoCodes` folder, then put the gct file in a `codes` folder at the root of your SD card. There are many sites and applications to create GCT files. If you feel nostlagic you might want to try my static version of [GeckoCodes.org](https://a-blondel.github.io/geckocodes.org/gct.html) ! 
  - Don't forget to enable Ocarina in Game Load settings in both cases.

