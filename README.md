# plexiglas

This piece of software was inspired by me buying the [WD My Passport Wireless Pro](https://www.wdc.com/products/portable-storage/my-passport-wireless-pro.html),
quite nice external hdd which is able to run [Plex](https://plex.tv) and stream all available
media across connected wireless devices. The only remarkable problem was is requirement
to manually copy required content to hdd, at least when you already have some instance
of Plex set up. But now, with plexiglas, you can easily have multiple servers with similar data.

**WARNING** upon loading `plexiglas` changes default PlexApi config path to `~/.config/plexiglas/config.ini`. 

## Features

* [ ] [Mobile Sync](https://support.plex.tv/articles/201082477-quick-guide-to-mobile-sync/), Plex Pass subscribers only
(therefore authentication with token is not supported in this mode)
    * [ ] Limit used space
* [ ] Stupid downloading of original video for those, who doesn't have Plex Pass
    * [ ] With configurable transcoding
    * [ ] Automatically remove watched videos
* [ ] Limit bandwidth
* [ ] Sync watch / seen status
