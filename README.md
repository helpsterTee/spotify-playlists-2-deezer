<img src="https://helpsterte.eu/img/projects/deezerhitsspotify.png" width="200"/>

# spotify-playlists-2-deezer
Upload your Spotify Playlists to Deezer with this Python3 application.

## Requirements
* Python 3
> pip install urwid

## How To Use
1. Use caseychu's [great playlist backup script](https://github.com/caseychu/spotify-backup) and export to JSON
   > python spotify-backup.py --format=json myplaylist.txt
2. [Register a new Deezer App](https://developers.deezer.com/) (they don't support the secret-less implicit grant OAuth as of now) **Be sure to leave redirect URL and domain as in the picture**
<img src="https://i.imgur.com/91cJaSa.png" width="600" />
3. Change the settings in spotify-restore.py to your APPID and Secret from the just registered Deezer App
<img src="https://i.imgur.com/qw0EWBJ.png" width="300" />
4. Launch the application

   > python spotify-restore.py myplaylist.txt
   <img src="https://i.imgur.com/jh1pDIo.png" width="600" />
5. Select or Deselect playlists, if needed. TAB switches focus to buttons on bottom. Space or Enter change selection
<img src="https://i.imgur.com/bpvpuZc.png" width="600" />
6. Start the import from the main menu, after saving. Some tracks will be not available on Deezer, those will be skipped.
<img src="https://i.imgur.com/L9QvcdT.png" width="400" />

**Note, this will take a long time, especially with a large number of playlists / large track count**
So get a coffee, brew some more, establish a coffee plantation business with fair trade principles, make some money and come back to check, if the script is finished.

Hint: The script will skip playlists that are already present on Deezer. So if you have any connection errors or timeouts, simply start again. It will pick up where it left.

## Contribute
1. Open issue describing the fix or improvement
2. Start Pull request, referencing the issue
3. Wait for approval or disapproval
