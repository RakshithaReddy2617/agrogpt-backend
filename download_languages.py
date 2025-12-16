from argostranslate import package

package.update_package_index()
packages = package.get_available_packages()

LANGS = [("en","te"),("te","en"),("en","hi"),("hi","en")]

for f,t in LANGS:
    pkg = next(p for p in packages if p.from_code==f and p.to_code==t)
    package.install_from_path(pkg.download())

print("✅ Language models installed")
