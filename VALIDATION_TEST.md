# Manual Validation Test - Step by Step

## Setup
1. **Kill old dev server**: Already done (PID 20652 killed)
2. **Start fresh dev server**: 
   ```bash
   cd C:\Users\Lenovo\Desktop\dyp\frontend
   npm run dev
   ```
3. **Hard refresh browser**: Ctrl + Shift + R (clears cache)

## Test Scenario 1: Truly Empty Form
**Goal**: Verify validation blocks empty submission

1. Sign in with a **NEW** Google account (one that hasn't completed questionnaire yet)
2. Check if "Full name" field is pre-filled or empty
3. If pre-filled, **CLEAR IT** manually
4. Click "Next" button
5. **Expected**: Error message "Full name is required" appears
6. **Expected**: Stays on Step 1

## Test Scenario 2: Pre-filled Google Name
**Goal**: Check if Google auto-fills the name

1. Sign in with Google
2. Look at "Full name" field on Step 1
3. **Is it pre-filled with your Google display name?** YES/NO
4. If YES, this explains why validation "passes" - the field isn't empty!

## Test Scenario 3: Minimal Submission
**Goal**: Can you submit with ONLY the name filled?

1. Have name filled (pre-filled from Google or typed)
2. Leave ALL other fields empty on Step 1
3. Click "Next" → Should go to Step 2 (name validation passed)
4. Leave ALL fields empty on Step 2
5. Click "Finish"
6. **Expected**: Form submits successfully (because ONLY name is required!)
7. **Result**: Shows "Health questionnaire completed"

## The Real Bug?

If Scenario 3 is what you're experiencing, then:
- ✓ Validation IS working (name is filled from Google)
- ✓ Form submission works (only name is required by backend)
- ✗ User THINKS they "filled nothing" (but name was pre-filled)

## Solution Options

**Option A**: Clear the pre-filled name so user must consciously fill it
**Option B**: Add validation messages showing "Auto-filled from Google account"
**Option C**: Make more fields required (age, sex, etc.)

## Debug Commands

```bash
# Check what name Google OAuth provides for you:
cd C:\Users\Lenovo\Desktop\dyp
.venv\Scripts\python.exe backend/manage.py shell
>>> from api.models import Profile
>>> for p in Profile.objects.all():
...     print(f"{p.email}: name='{p.full_name}'")
... 
>>> exit()
```

## Next Steps

1. Restart dev server with fresh code
2. Hard refresh browser
3. Run Test Scenario 3 to confirm the REAL bug
4. Report back which scenario matches your experience
