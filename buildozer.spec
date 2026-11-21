[app]
title = Unchanged
package.name = unchanged
package.domain = org.unchangedgame
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.5
icon.filename = %(source.dir)s/icon.jpg
requirements = python3,pygame
orientation = landscape
fullscreen = 1
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
