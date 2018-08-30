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
* [ ] Simple downloading of original video for those, who don't have PlexPass. Please see [Plex Downloader](https://github.com/danstis/PlexDownloader) for now
    * [ ] With configurable transcoding
    * [ ] Automatically remove watched videos
* [X] Mark missing videos as watched
* [X] Limit bandwidth
* [ ] Trailers downloading & converting to mp4

## Installation

```
pip install --process-dependency-links plexiglas
```

Option `--process-dependency-links` is a temporary requirement, while plexapi doesn't have sync api.

## Usage

```
plexiglas -d "/Volumes/My Passport/PlexSync" --limit-disk-usage 10% -w
```

Following arguments are currently supported:

* `-u`, `--username` — your Plex.tv username, after the first run in will be securely stored in a keychain
* `-p`, `--password` — your Plex.tv password, after the first run in will be securely stored in a keychain
* `-d`, `--destination` — the path where to store downloaded files and Plexiglas' DB, current dir by default. Do not
forget to copy `.plexiglas.db` file to the new path manually, If you'd like to change the folder
* `-w`, `--mark-watched` — if a previously downloaded file is missing within destination directory the media would be
marked as watched
* `--debug` — enable debug logging
* `-v`, `--verbose` — enable logging from underlying library (plexapi)
* `-s`, `--limit-disk-usage` — sets disk usage limit, supported human-readable format and percents of total disk space
* `--loop` — run the script in a loop, so it will monitor for updates
* `--delay` — sets delay (in seconds) between iterations
* `-n`, `--device-name` — allows to set human-readable device name instead of computer name
* `-r`, `--resume-downloads` — restart download if file is exist
* `--rate-limit` — limit bandwidth usage
* `-q` — close application right after initialization and storing all required data in keyring
* `-i`, `--insecure` — use insecure keyring, which can be used in non-interactive mode

If you wouldn't provide a username and/or password the app will ask you to provide them in interactive mode
