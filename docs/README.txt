Dwarf Fortress - Japanese localization (dfint-ja)
=================================================

An unofficial, fan-made Japanese localization for the Steam release of
Dwarf Fortress (Premium, Windows, version 53.17).

Site:    https://higesho.github.io/df-ja/   (Japanese)
Source:  https://github.com/higesho/df-ja


Install
-------

Copy the contents of this zip into your Dwarf Fortress folder.

  (for example)  C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\

That puts three things in place:

  dfhooks.dll           chainloader
  dfhooks_dfint_ja.dll  the translation engine
  dfint-data\           dictionaries, font, config

Nothing belonging to the game is modified. "Dwarf Fortress.exe" and everything
under "data\" are left untouched.

If you use DFHack
  DFHack installs its own "dfhooks.dll", so you already have that file.
  DO NOT OVERWRITE IT. Copy only the other two items (dfhooks_dfint_ja.dll and
  dfint-data\) and it will work. Installing DFHack afterwards works too — leave
  it to DFHack's own dfhooks.dll and nothing else needs changing.


Uninstall
---------

Delete the three items listed above.

  dfhooks.dll           (keep this one if you use DFHack)
  dfhooks_dfint_ja.dll
  dfint-data\


Using it
--------

- Press Ctrl+F2 in game to turn the translation on and off.
- If the text shows as boxes, check that the font is present in
  dfint-data\fonts\.


Reporting untranslated text
---------------------------

Open dfint-data\config.txt and change

  [LOG_LEVEL:Warn]

to

  [LOG_LEVEL:Debug]

Untranslated strings are then recorded in dfint-data\dfint-log.log. The log is
rewritten every time the game starts, so copy it before you quit.

Please report mistranslations and anything left in English at
https://github.com/higesho/df-ja/issues


Known limitations
-----------------

- Personal names, place names and the names the game generates for each world
  stay in English. There is nothing to look them up in.
- The game decides field widths from the English text, so a longer Japanese
  string can overlap the next column. Where it was noticeable the text is cut
  with a trailing ellipsis.
- With DFHack, its tab labels (Automation and so on) and tool ids stay in
  English.
- A game update moves the hooked functions and will break this mod until it is
  rebuilt.


Credits and rights
------------------

- The engine is based on dfint/df-steam-hook-rs and its Simplified Chinese
  fork dfint-rust-cjk, both MIT licensed. See LICENSE\LICENSE.
- The font is Noto Sans Mono CJK JP Bold, SIL Open Font License 1.1.
  See LICENSE\OFL-LICENSE.txt.
- The translation data was written for this project.
- Dwarf Fortress itself belongs to Bay 12 Games / Kitfox Games.

Unofficial mod. Back up your saves before using it.
