### 📌 Refactor Note: PlanOption Schema Placement

**Issue:**
`PlanOption` is currently defined inside `workers` schema but is also used in `policies`. This creates a cross-domain dependency and breaks clean separation of concerns.

**Why it matters:**

* Plans are a separate domain concept (not worker-specific)
* Reusing it across modules can lead to tight coupling
* Harder to maintain and scale as project grows

**What to do (Post Phase 1):**

1. Create a new file: `schemas/plans.py`
2. Move `PlanOption` into this file
3. Update imports:

   ```python
   from schemas.plans import PlanOption
   ```
4. Replace any `list` usages with:

   ```python
   List[PlanOption]
   ```

**Priority:** Medium (safe to defer until Phase 1 completion)

**Impact:** Improves code organization, reusability, and long-term maintainability

⚠️ What could be improved (because I refuse to let you get comfortable)

status: str → should be Enum (active, pending, etc.)
no validation for plan_name → risky
no currency typing (float is dangerous for money long-term)

### 📌 Refactor Note: PremiumCalculator Return Structure

**Current State:**
`calculate_all_plans()` returns a tuple → `(plans, recommended)`

**Issue:**

* Not self-descriptive
* Can lead to confusion or unpacking errors
* Not aligned with structured API responses

**Future Improvement:**
Refactor to return a dictionary:

```python
{
  "plans": [...],
  "recommended": "smart_protect"
}
```

**Migration Steps (later):**

1. Update function return type
2. Update all usages:

   ```python
   result = calculate_all_plans(...)
   plans = result["plans"]
   recommended = result["recommended"]
   ```
3. Ensure API responses match `PlanListResponse`

**Priority:** Low (safe to defer until Phase 1 completion)


⚠️ Subtle issue (you knew I wouldn’t let this slide)

You’re catching all exceptions:

except Exception as e:

Which is fine for now… but:

you’re returning error details directly

In production:

this can leak internal info
stack traces
connection details

⚠️ Issues (very few, but I’m not letting you escape clean)
❗ Issue 1: print() instead of logging

You wrote:

print("🚀 Server ready...")
🧠 Problem
no log levels
not structured
useless in production systems
✅ Fix (simple upgrade)
import logging

logger = logging.getLogger(__name__)

logger.info(f"{settings.APP_NAME} starting...")
⚠️ Issue 2: CORS wide open
allow_origins=["*"]
🧠 Reality

Fine now. Dangerous later.

✅ Dev note (don’t fix now)

Later:

allow_origins=["http://localhost:3000"]
⚠️ Issue 3: DB init in app (acceptable but temporary)
await init_db()
🧠 Reality