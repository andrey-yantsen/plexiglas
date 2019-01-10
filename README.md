# plexiglas

This piece of software was inspired by me buying the [WD My Passport Wireless Pro](https://www.wdc.com/products/portable-storage/my-passport-wireless-pro.html),
quite nice external hdd which is able to run [Plex](https://plex.tv) and stream all available
media across connected wireless devices. The only remarkable problem was is requirement
to manually copy required content to hdd, at least when you already have some instance
of Plex set up. But now, with plexiglas, you can easily have multiple servers with similar data.

## Features

* [X] [Mobile Sync](https://support.plex.tv/articles/201082477-quick-guide-to-mobile-sync/), Plex Pass subscribers only
    * [X] Limit used space
    * [ ] Minimize transcoding somehow (no idea if it's possible)
* [X] Work with Python 2.7
    * [X] Work on WD My Passport Wireless Pro ([docs](https://github.com/andrey-yantsen/plexiglas/wiki/Running-from-WD-My-Passport-Wireless-Pro))
        * [X] Run and able to download files
        * [X] Keyring is working
* [X] Resume transfer
* [X] Simple downloading of original video for those, who don't have PlexPass
    * [ ] With configurable transcoding
    * [X] Automatically remove watched videos
    * [ ] Download all video parts, not only first
* [X] Mark missing videos as watched
* [X] Limit bandwidth
* [ ] Trailers downloading & converting to mp4
* [X] Confirmed working with Movies & TV-Shows
    * [X] mobile sync
    * [X] simple sync
* [ ] Confirmed working with audio
    * [X] mobile sync
    * [ ] simple sync
* [ ] Confirmed working with photo
    * [X] mobile sync
    * [ ] simple sync
* [ ] Confirmed working with playlists
    * [X] mobile sync
    * [ ] simple sync
* [ ] --subdir as plugin
* [ ] Sync watching position

## Installation

```
pip install plexiglas
```

(sudo may be required)

If you'll receive an error like `AttributeError: 'MyPlexAccount' object has no attribute 'syncItems'`
it means that you already have PlexAPI installed, but without my changes, to fix this please execute
following commands:

```
pip uninstall plexapi
pip install 'plexapi>=3.1.0'
```


## Usage

```
plexiglas -d "/Volumes/My Passport/PlexSync" --limit-disk-usage 10% -w
```

Following arguments are currently supported:

* `-u`, `--username` — your Plex.tv username, after the first run in will be securely stored in a keychain
* `-p`, `--password` — your Plex.tv password, after the first run in will be securely stored in a keychain
* `-n`, `--device-name` — allows to set human-readable device name instead of computer name
* `-d`, `--destination` — the path where to store downloaded files and Plexiglas' DB, current dir by default. Do not
    forget to copy `.plexiglas.db` file to the new path manually, If you'd like to change the folder
* `-w`, `--mark-watched` — if a previously downloaded file is missing within destination directory the media would be
    marked as watched
* `--debug` — enable debug logging
* `-v`, `--verbose` — enable logging from underlying library (plexapi)
* `-s`, `--limit-disk-usage` — sets disk usage limit, supported human-readable format and percents of total disk space
* `--loop` — run the script in a loop, so it will monitor for updates
* `--delay` — sets delay (in seconds) between iterations
* `-r`, `--resume-downloads` — restart download if file is exist
* `--rate-limit` — limit bandwidth usage
* `-q` — close application right after initialization and storing all required data in keyring
* `-i`, `--insecure` — use insecure keyring, which can be used in non-interactive mode
* `--skip` — skip specified file from downloading, can be used multiple times. E.g. passing `Rewatch/The Butterfly Effect (2004).mp4`
    as an argument will skip the movie `The Butterfly Effect` from downloading to `sync` named `Rewatch`
* `--subdir` — store each movie in subdirectory, so you can easily add extras (e.g. [trailers](https://github.com/andrey-yantsen/plexiglas/wiki/Downloading-trailers))
* `--simple-sync-url` — download media from specific part of the library, you should enter argument value in format `URL [<COUNT> [<ALLOW_WATCHED>]]`, where items in square braces are optional.
    To get the URL simply open your Plex Web UI, go to the library you're interested in (syncing for single items like
    Movie, TVShow, Season also supported), set any required filters and / or sorting and copy the resulting URL from the
    browser. Sample usage:
    * Download 10 unwatched movies, sorted by year of release (all filters and sorting are set in Plex Web UI)
    ```
    --simple-sync-url https://app.plex.tv/desktop#!/server/607c8c938b50eef734456f8b9da94b5d02339ce5?key=%2Flibrary%2Fsections%2F1&typeKey=%2Flibrary%2Fsections%2F1%2Fall%3Ftype%3D1&save=1&limit=&sort=year%3Adesc 10
    ```
    * Download 5 oldest watched movies:
    ```
    --simple-sync-url http://example.com:32400/web/index.html#!/server/607c8c938b50eef734456f8b9da94b5d02339ce5?key=%2Flibrary%2Fsections%2F1&typeKey=%2Flibrary%2Fsections%2F1%2Fall%3Ftype%3D1&customFilter=1&save=1&sort=lastViewedAt&filters=unwatched%21%3D1 5 1
    ```

If you wouldn't provide a username and/or password the app will ask you to provide them in interactive mode, afterwards
it will be stored in secure storage, unless option `-i` was set.

If you're using Mobile Sync you can split all your files by subdirectories in quite an easy way:
when you create a new Sync Item in Plex interface it asks you for a `title` — it would be a folder
name for all the items, related to this item. And there lies a trick, there is some special handling
for this title:

* You can set it to something like `Movies#Best` — in this case the part after `#` will be ignored 
  and all the files would be placed within `Movies` folder, while you'll be able to differentiate
  Sync Items in the interface
* You can use `/` or `\\` to split the files by folders, e.g. you can add a new Item
  `TV Shows/The Big Gang Theory` and all the episodes will be stored inside directory
  `TV Shows/The Big Gang Theory` of your downloading path.   
