[app]
title = Unchanged
package.name = unchanged
package.domain = org.unchangedgame
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.7
icon.filename = %(source.dir)s/icon.jpg
requirements = python3==3.11.6,kivy==2.3.0,pillow==10.4.0
orientation = landscape
fullscreen = 1
android.archs = arm64-v8a
android.api = 33
android.minapi = 21
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
