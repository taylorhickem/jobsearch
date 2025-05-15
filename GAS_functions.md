# 🧰 Google Apps Script Functions Reference

## `recordTrackAssignments()`

**Purpose**: Transfers manually selected `jobid` and `track_id` pairs from `track_un` to `track_assignment`, clearing the source assignments afterward.

**Logic**:

* Reads `track_un!A:B` (jobid, track\_id)
* Appends valid rows (with non-empty `track_id`) to `track_assignment!A:B`
* Clears processed values in `track_un!B`

---

## `selectApplySuccess()`

**Purpose**: Updates the `apply` column in `screened` based on application success stored in `apply_results`.

**Logic**:

* Scans `apply_results!A:B` and builds a `Set` of `jobid`s with `apply_status = 1`
* Loops through `screened!E:R`, setting `apply = 1` if jobid is found in the set, else clears it
* Writes back only the updated `R` column (apply)

**Usage**: Called inside `recordApplications()` to synchronize UI status before copying jobs to `open`

---

## `clearApplyInProcess()`

**Purpose**: Cleans up the `apply_results` sheet, keeping only jobids that remain unclosed and have `apply ≠ 1`.

**Logic**:

* From `screened!E:R:W`, builds a `Set` of jobids where `apply ≠ 1` and `closed == 0`
* Filters `apply_results!A:D` to retain only these jobids
* Clears the sheet and rewrites only retained rows

**Usage**: Called inside `recordApplications()` to remove outdated in-process records

---

## `recordApplications()`

**Purpose**: Appends selected leads from `screened` to `open`, logs application status, and resets the `apply` selector

**Logic**:

1. Calls `selectApplySuccess()` to refresh `screened.apply`
2. Filters `screened` for `apply = 1`, builds application rows
3. Appends those rows to `open`
4. Clears `apply` flag from selected leads
5. Calls `clearApplyInProcess()` to prune stale `apply_results`

**Menu Integration**: Appears in `JobsearchApp` custom menu

---

## `closeLeads()`

**Purpose**: Archives leads from the `open` sheet marked as closed and preserves others.

**Logic**:

* Reads all rows below the `open_hdr` range
* Moves rows with `closed = 1` to `closed` sheet, adds timestamp
* Retains only `open` leads in original sheet

**Menu Integration**: Appears in `JobsearchApp` custom menu

---
