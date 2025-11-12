#!/usr/bin/env python3
import argparse, re, pathlib, sys

def read_srt(p):
    blocks, cur, buf = [], None, []
    for line in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
        if line.strip() == "":
            if cur:
                blocks.append((cur[0], cur[1], "\n".join(buf).strip()))
                cur, buf = None, []
            continue
        if cur is None and re.match(r"^\d+$", line.strip()):
            cur = [line.strip(), None]
            continue
        if cur and cur[1] is None and "-->" in line:
            cur[1] = line.strip()
            continue
        buf.append(line)
    if cur:
        blocks.append((cur[0], cur[1], "\n".join(buf).strip()))
    return blocks

def write_srt(blocks, outp):
    lines=[]
    for i,(idx,ts,txt) in enumerate(blocks,1):
        lines += [str(i), ts, txt, ""]
    pathlib.Path(outp).write_text("\n".join(lines), encoding="utf-8")

def ensure_en_de_translator():
    """Ensure EN->DE translation package is installed and return translator."""
    try:
        import argostranslate.package
        import argostranslate.translate

        # Update package index
        try:
            argostranslate.package.update_package_index()
        except Exception as e:
            print(f"Warning: could not update package index ({e}); continuing with local cache.", file=sys.stderr)

        # Check if EN->DE package is installed
        installed = argostranslate.package.get_installed_packages()
        has_en_de = any(p.from_code == "en" and p.to_code == "de" for p in installed)

        if not has_en_de:
            # Get available packages and find EN->DE
            available = argostranslate.package.get_available_packages()
            en_de_pkg = next((p for p in available if p.from_code == "en" and p.to_code == "de"), None)
            
            if not en_de_pkg:
                raise RuntimeError("No Argos EN->DE package found in index.")
            
            # Download and install
            download_path = en_de_pkg.download()
            argostranslate.package.install_from_path(download_path)

        # Get installed languages and find translator
        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = next((lang for lang in installed_languages if lang.code == "en"), None)
        to_lang = next((lang for lang in installed_languages if lang.code == "de"), None)
        
        if not from_lang or not to_lang:
            raise RuntimeError("EN or DE language not found after installation.")
        
        translation = from_lang.get_translation(to_lang)
        if not translation:
            raise RuntimeError("Could not get EN->DE translation object.")
        
        return translation
    except Exception as e:
        raise RuntimeError(f"Argos setup failed: {e}")

def translate_texts(texts):
    try:
        translator = ensure_en_de_translator()
        out = [translator.translate(t) if t.strip() else t for t in texts]

        # Basic sanity check: if nothing changed and there were non-empty lines, warn
        changed = any((a.strip() != b.strip()) for a, b in zip(texts, out) if a.strip())
        if not changed and any(t.strip() for t in texts):
            raise RuntimeError("Translation produced no changes; likely model/setup issue.")

        return out
    except Exception as e:
        # Fail loudly so the pipeline signals the problem instead of silently outputting English
        raise SystemExit(f"ERROR: {e}. Could not produce a German SRT.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_srt_en", required=True)
    ap.add_argument("--out_srt_de", required=True)
    args = ap.parse_args()

    blocks = read_srt(args.in_srt_en)
    texts = [b[2] for b in blocks]
    de = translate_texts(texts)
    out = [(b[0], b[1], de[i]) for i,b in enumerate(blocks)]
    pathlib.Path(args.out_srt_de).parent.mkdir(parents=True, exist_ok=True)
    write_srt(out, args.out_srt_de)
    print("OK: DE SRT written")

if __name__ == "__main__":
    main()
