import os, subprocess, json
import constants
import logging
import yaml

logger = logging.getLogger("harness.helpers")

def flatten_yaml(data, prefix=""):
    """Flatten nested dict to dot-separated paths"""
    result = {}
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(flatten_yaml(value, full_key))
            else:
                result[full_key] = value
    return result


def load_crd_schema(kind):
    """Load CRD YAML and extract the OpenAPI schema for a given Kind"""
    crd_path = constants.SCHEMA_MAP.get(kind)
    if not crd_path:
        logger.warning(f"No CRD found for Kind: {kind}")
        return None
    
    with open(os.path.join(constants.SCHEMA_DIR, crd_path), "r") as f:
        crd = yaml.safe_load(f)
    
    # Extract the OpenAPI v3 schema from the CRD
    for version in crd["spec"]["versions"]:
        if "schema" in version and "openAPIV3Schema" in version["schema"]:
            return version["schema"]["openAPIV3Schema"]
    
    # Older CRD format
    if "validation" in crd["spec"] and "openAPIV3Schema" in crd["spec"]["validation"]:
        return crd["spec"]["validation"]["openAPIV3Schema"]
    
    logger.warning(f"No OpenAPI schema found in CRD for Kind: {kind}")
    return None

def extract_valid_paths(schema, prefix=""):
    """Recursively walk the JSON schema and collect all valid field paths"""
    valid_paths = set()
    
    if "properties" in schema:
        for field, field_schema in schema["properties"].items():
            full_path = f"{prefix}.{field}" if prefix else field
            valid_paths.add(full_path)
            
            # Recurse into nested objects
            if field_schema.get("type") == "object":
                valid_paths.update(extract_valid_paths(field_schema, full_path))
            
            # Handle arrays with object items
            if field_schema.get("type") == "array":
                items = field_schema.get("items", {})
                if items.get("type") == "object":
                    valid_paths.update(extract_valid_paths(items, full_path + "[]"))
    
    return valid_paths

def flatten_yaml_paths(data, prefix=""):
    """Flatten the LLM's YAML into all field paths present"""
    paths = set()
    
    if isinstance(data, dict):
        for key, value in data.items():
            full_path = f"{prefix}.{key}" if prefix else key
            paths.add(full_path)
            if isinstance(value, dict):
                paths.update(flatten_yaml_paths(value, full_path))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        paths.update(flatten_yaml_paths(item, full_path + "[]"))
    
    return paths

def validate_against_crd(yaml_spec):
    """Check every field in the YAML against the CRD schema"""
    kind = yaml_spec.get("kind")
    schema = load_crd_schema(kind)
    
    if schema is None:
        return None
    
    valid_paths = extract_valid_paths(schema)
    yaml_paths = flatten_yaml_paths(yaml_spec)
    
    # Skip standard K8s fields
    skip = {"apiVersion", "kind", "metadata", "metadata.name", 
            "metadata.namespace", "metadata.labels", "metadata.annotations"}
    
    yaml_paths = yaml_paths - skip
    
    hallucinated = []
    valid = []
    
    for path in yaml_paths:
        # Check if this path or any parent array path exists in schema
        # e.g. spec.backupPlanComponents[].selector matches 
        #      spec.backupPlanComponents[].selector in schema
        if path_exists_in_schema(path, valid_paths):
            valid.append(path)
        else:
            hallucinated.append(path)
    
    return {
        "hallucinated": hallucinated,
        "valid": valid,
        "total_fields": len(yaml_paths),
        "schema_paths_count": len(valid_paths)
    }

def path_exists_in_schema(path, valid_paths):
    """Check if a YAML path exists in the schema valid paths.
    Handles array notation differences."""
    
    # Direct match
    if path in valid_paths:
        return True
    
    # Try with array notation
    # LLM YAML: spec.backupPlanComponents.selector
    # Schema:   spec.backupPlanComponents[].selector
    parts = path.split(".")
    for i in range(len(parts)):
        # Try inserting [] after each segment
        candidate = ".".join(parts[:i+1]) + "[]"
        if i + 1 < len(parts):
            candidate += "." + ".".join(parts[i+1:])
        if candidate in valid_paths:
            return True
    
    # Try parent path exists (for deeply nested objects without
    # full schema definition)
    parent = ".".join(parts[:-1])
    if parent in valid_paths:
        return True
    
    return False