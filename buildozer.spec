[app]
title = Unchanged
package.name = unchanged
package.domain = org.unchangedgame
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 2.0
icon.filename = %(source.dir)s/icon.jpg
requirements = python3,kivy
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
