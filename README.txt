Habitica Quest Accept
=====================

This program checks Habitica once a day and accepts a party quest
invitation that is still waiting for your answer.

It uses the Habitica account you connect during setup. A quest you
already accepted stays accepted. A quest you already declined stays
declined. Your User ID and API Token stay in a file on this computer.

The computer should be on around the time you pick. If it was asleep,
the check usually runs after the computer wakes.


You need
--------

1. A Habitica account. Create one or log in:

   https://habitica.com

2. Python 3.9 or newer.

   Windows: https://www.python.org/downloads/windows/
   Mac:     https://www.python.org/downloads/macos/

   On the Windows installer, turn on "Add python.exe to PATH"
   before you click Install.


Get your Habitica User ID and API Token
----------------------------------------

These are the two codes the program uses to act for you. The API Token
works like a password. Do not email it, post it, or put it in a chat.

1. Log in on the Habitica website:

   https://habitica.com

2. Open the API page. This link goes straight there:

   https://habitica.com/user/settings/api

   You can also get there by clicking your user icon at the top of the
   page, then Settings, then API.

   A written tour of that page, with the same two codes labeled:

   https://habitica.fandom.com/wiki/API_Options

3. On that page, find User ID. It looks like this:

   12345678-90ab-416b-cdef-1234567890ab

   Copy the whole thing, including the dashes.

4. On the same page, click "Show API Token". Copy that second code too.
   It has the same shape, and it is the secret one.

   On the phone app: open the menu, then Settings, then API. Tap the
   User ID to copy it, then tap the API Token to copy it. The website
   link above is the surest place to copy both.

5. If you ever paste the API Token somewhere public, ask Habitica to
   reset it. On the website use Help, then Report a Bug. You can also
   write to admin@habitica.com from the email address on your account.
   Say that the token was exposed. Do not include the token in the email.

   Habitica's own description of the API, for anyone who wants it:

   https://habitica.com/apidoc/


Install (about two minutes)
----------------------------

1. Unzip this folder somewhere you can find again, such as Documents.
   Leave the files together in that one folder.

2. Mac: double-click install.command.
   If the Mac says it cannot be opened, Control-click install.command,
   choose Open, then choose Open again.

   Windows: double-click install.bat.

3. The window asks for your User ID, then your API Token. The token
   will not appear as you paste it. Paste it anyway, then press Enter.

   It then asks what time of day to check. Press Enter for 8:00 in
   the morning, or type a time such as 21:30.

4. The window checks the codes with Habitica, then installs the daily
   run. It offers to accept a waiting quest immediately. Press Enter
   for yes.

5. The window should end with the word Installed. Press Enter to close it.


Check that it worked
--------------------

Mac: double-click run_now.command
Windows: double-click run_now.bat

A line that says OK means the program reached Habitica.

  OK no quest invitation     nobody is waiting on you right now
  OK accepted                it accepted a quest invitation
  OK already accepted        you had already accepted it
  OK ... stays declined      you had declined it, and it was left declined
  FAIL                       the codes or the network need another look

The same lines are saved in this folder:

  logs\quest-accept.log        on Windows
  logs/quest-accept.log        on Mac


Run it from a command window
----------------------------

Mac: open Terminal. Type cd, then a space, then drag this folder onto
the Terminal window, then press Enter. Then type:

  python3 install.py

Windows: open Command Prompt. Type cd /d and a space, then drag this
folder onto the window, then press Enter. Then type:

  py -3 install.py

To look without accepting:

  Mac:     .venv/bin/python habitica_quest_accept.py --check
  Windows: .venv\Scripts\python.exe habitica_quest_accept.py --check

Before the installer has created .venv, use python3 or py -3 in place
of that .venv path.


Change the time or the account
-------------------------------

Run the installer again. It replaces the daily schedule and can replace
the saved User ID and API Token.


Uninstall
---------

Mac: double-click uninstall.command
Windows: double-click uninstall.bat

That removes the daily run. It asks before it deletes the saved token.
Your Habitica account is unchanged.


Give this folder to someone else
---------------------------------

Send them a fresh unzipped copy, or a zip made before anyone's token
was saved. Do not send config.json, the .venv folder, or the logs
folder. Those can contain your API Token.

The person who packages the download can build a clean zip with:

  python3 make_dist.py

The zip is written under dist\ and does not include config.json.


What the program talks to
--------------------------

Only Habitica, at:

  https://habitica.com/api/v3

It reads your account and your party, and it accepts a quest invitation
that is still waiting. It does that with the official quest-accept call
documented at:

  https://habitica.com/apidoc/
