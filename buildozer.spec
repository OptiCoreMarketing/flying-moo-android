[app]

# Appens navn, som vises under ikonet på telefonen
title = Flying Moo

# Internt pakkenavn (ingen mellemrum eller specialtegn)
package.name = flyingmoo

# Omvendt domæne - bruger jeres eget domæne corehost.one
package.domain = one.corehost

# Hvor kildekoden ligger
source.dir = .

# Hvilke filtyper skal pakkes med ind i appen
source.include_exts = py,png,jpg,jpeg,kv,atlas,json

# Versionsnummer, vises for brugeren og bruges internt af Android
version = 1.0

# Python-pakker appen har brug for
requirements = python3,kivy

# Skærmretning: landscape (liggende), matcher spillets design
orientation = landscape

# Fuldskærm uden Android-statusbar
fullscreen = 1

# Android-specifikke indstillinger
android.api = 34
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

# Ikon og præsentationsskærm (valgfrit, kan tilføjes senere)
# icon.filename = %(source.dir)s/icon.png

[buildozer]

log_level = 2
warn_on_root = 1
