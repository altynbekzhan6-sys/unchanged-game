[app]
title = Unchanged
package.name = unchanged
package.domain = org.unchangedgame
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.5
icon.filename = %(source.dir)s/icon.jpg
requirements = hostpython3==3.11.6,python3==3.11.6,cython==0.29.36,pygame==2.6.1
orientation = landscape
fullscreen = 1
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True
[buildozer]

log_level = 2
warn_on_root = 1
