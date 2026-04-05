# Install VS Code Extension:
---
- Install: AWS CloudFormation / CloudFormation Linter
- Create file: ec2.yaml (or .yml)
- Type: start → auto-generates template (snippet)
- Keep only required sections
- Remove or comment unused sections (do NOT leave empty keys)
---

# CloudFormation Rules:
**Any section you leave empty like this will break cfn-lint**, not just `Metadata`.

---

### 🔴 Problem pattern (causes error)

```yaml
Description:
Metadata:
Mappings:
Conditions:
Resources:
Outputs:
```

👉 All of these become `null` → linter crashes or throws errors

---

### ✅ Fix (apply everywhere)

#### ✔ Option 1 — Remove unused sections (BEST)

```yaml
AWSTemplateFormatVersion: 2010-09-09

Resources:
  myVPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
```

---

#### ✔ Option 2 — Use empty objects

```yaml
Description: ""
Metadata: {}
Mappings: {}
Conditions: {}
Resources: {}
Outputs: {}
```

---

#### ✔ Option 3 — Comment them

```yaml
# Metadata:
# Mappings:
# Conditions:
# Outputs:
```

---

### ⚠️ Important rule

| Section     | Can be empty?               | Recommended          |
| ----------- | --------------------------- | -------------------- |
| Description | ❌ (don’t leave blank)       | Use string or remove |
| Metadata    | ❌                           | `{}` or remove       |
| Parameters  | ❌                           | `{}` or remove       |
| Mappings    | ❌                           | `{}` or remove       |
| Conditions  | ❌                           | `{}` or remove       |
| Resources   | ❌ (must exist if deploying) | Required             |
| Outputs     | ❌                           | `{}` or remove       |

---

### 🔥 Why this happens (quick)

YAML:

```yaml
Metadata:
```

=

```json
"Metadata": null
```

But `cfn-lint` expects:

```json
"Metadata": {}
```

---

### 💡 Pro DevOps tip

In real projects:

* Keep only:

  * `AWSTemplateFormatVersion`
  * `Description`
  * `Resources`
* Add others **only when needed**

---

### 🎯 Final takeaway

👉 **Never leave any key empty in YAML CloudFormation**
👉 Either **remove, comment, or use `{}`**

---
