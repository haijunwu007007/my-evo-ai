"""Fix self._config -> self.config and add module_class export to all rewritten modules."""

import re

# Modules that need _config -> config fix
config_fixes = {
    "postgres_db.py": ("PostgresDBModule", "postgres_db"),
    "mongodb_nosql.py": ("MongoDBModule", "mongodb_nosql"),
    "redis_cache.py": ("RedisCacheModule", "redis_cache"),
    "object_storage.py": ("ObjectStorageModule", "object_storage"),
}

# Modules that need config added + module_class
config_add = {
    "elasticsearch_search.py": ("ElasticSearchModule", "elasticsearch_search"),
}

# Modules that just need module_class export
mc_only = {
    "page_cache.py": ("PageCacheModule", "page_cache"),
}


def fix_config(filename):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("self._config", "self.config")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Fixed self._config -> self.config in {filename}")


def add_module_class(filename, class_name):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    export = f"\nmodule_class = {class_name}\n"
    if export.strip() not in content:
        # Append before if __name__ block or at end
        if "if __name__ == '__main__':" in content:
            content = content.replace("if __name__ == '__main__':", export + "\nif __name__ == '__main__':")
        else:
            content = content.rstrip() + "\n" + export
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Added module_class = {class_name} to {filename}")
    else:
        print(f"  module_class already exists in {filename}")


def add_config_attr(filename):
    """For elasticsearch_search which has no config usage at all"""
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    if "self.config" not in content:
        # Add after super().__init__(config) line
        content = content.replace(
            "super().__init__(config)", "super().__init__(config)\n        self.config = config or {}"
        )
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Added self.config to {filename}")


print("=== Fixing config attributes ===")
for f, (cls, mid) in config_fixes.items():
    fix_config(f)
    add_module_class(f, cls)

print("\n=== Adding config + module_class ===")
for f, (cls, mid) in config_add.items():
    add_config_attr(f)
    add_module_class(f, cls)

print("\n=== Adding module_class only ===")
for f, (cls, mid) in mc_only.items():
    add_module_class(f, cls)

print("\nDone!")
