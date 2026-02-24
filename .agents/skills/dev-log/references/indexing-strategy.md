# Indexing Strategy

## Index Update Rules

### Adding Findings
1. Scan existing findings files → find max sequence number
2. Create `findings/findings.NNN-topic.md` (max + 1)
3. Add entry to `findings.index.md`:
   - Number (NNN), file path, date, one-line summary (max 30 chars), keywords (3-5)

### Adding Progress
1. Check if today's progress file already exists
2. **If exists** → append to existing file; **if not** → create new file
3. Add entry to `progress.index.md` at **top**:
   - Date, file path, one-line summary (max 30 chars), tags (3-5)

### Adding Decisions
1. Scan existing decision files → find max sequence number
2. Create `decisions/decision-NNN-topic.md` (max + 1)
3. Add entry to `decisions.index.md`:
   - Number (NNN), file path, date, status (draft/accepted/rejected), one-line summary, keywords
4. When status changes, update the index status field accordingly

## Sequence Collision Prevention

Before creating findings/decision files:
1. List the target directory
2. Extract sequence numbers from filenames (e.g., `findings.015-topic.md` → 15)
3. Create new file with max sequence + 1
4. Maintain sorted order by sequence in the index
