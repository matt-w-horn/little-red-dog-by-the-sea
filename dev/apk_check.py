"""Does the built APK hold the art folder as it is now? Used by merge_poses.sh.

    python3 -I dev/apk_check.py APK ART

Every file under ART but art/reference/ (which the app does not package) must be in the APK under assets/art/ with
the same bytes, and the APK must hold no other file there. Gradle does not write the APK again when nothing changed,
so the APK's age says nothing; its contents do.
"""
import sys
import zipfile
from pathlib import Path


def main():
    apk, art = zipfile.ZipFile(sys.argv[1]), Path(sys.argv[2])
    packed = {n[len('assets/art/'):]: n for n in apk.namelist() if n.startswith('assets/art/')}
    files = {str(p.relative_to(art)): p for p in art.rglob('*')
             if p.is_file() and p.relative_to(art).parts[0] != 'reference' and p.name != '.DS_Store'}
    bad = [f'{n}: not in the APK' for n in sorted(set(files) - set(packed))]
    bad += [f'{n}: in the APK, not in the art folder' for n in sorted(set(packed) - set(files))]
    bad += [f'{n}: the APK holds other bytes' for n in sorted(set(files) & set(packed))
            if apk.read(packed[n]) != files[n].read_bytes()]
    for line in bad[:10]:
        print('  ', line)
    print(f'   APK: {len(packed)} art files; art folder: {len(files)}; '
          + ('RESULT: the APK holds the art folder' if not bad else f'RESULT: {len(bad)} DIFFER'))
    sys.exit(1 if bad else 0)


main()
