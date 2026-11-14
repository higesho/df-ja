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


Other mods
----------

Raw mods (creatures, items, materials), tilesets and graphics mods work
alongside this one. Nothing in the game's data is read while playing - the
engine only looks at the text being drawn - so a modded world can have this
added or removed freely.

- Names a mod adds are not in the dictionary, so they stay in English.
  Nothing is left half-translated: a name that cannot be looked up in full
  is drawn as it is.
- A name built out of vanilla words ("cave dragon") may come out in Japanese
  anyway, because names are translated from their parts.
- To get a mod's own names translated, log them (see below) and report them,
  or add them to the dictionaries yourself and rebuild. The engine itself
  does not need touching.

The exception is a mod that ships its own "dfhooks.dll". Only one such file
can be in place, so it cannot be used at the same time. For DFHack, see
Install above.


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
