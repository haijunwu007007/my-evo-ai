"""修复文件中重复的 module_class = 定义"""
import os, glob

modules_dir = "modules"
count = 0
for fp in glob.glob(os.path.join(modules_dir, "*.py")):
    fname = os.path.basename(fp)
    if fname.startswith("_") or fname == "__init__.py":
        continue
    with open(fp, encoding="utf-8") as f:
        lines = f.readlines()

    seen = set()
    new_lines = []
    changed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("module_class ="):
            if stripped in seen:
                changed = True
                continue  # skip duplicate
            seen.add(stripped)
        new_lines.append(line)

    if changed:
        with open(fp, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"  ✓ {fname}: 去重")
        count += 1

print(f"\n共修改 {count} 个文件")
