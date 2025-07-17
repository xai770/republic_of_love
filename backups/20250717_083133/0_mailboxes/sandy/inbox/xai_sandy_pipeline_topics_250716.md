

## 07:21
Hey Sandy, nice progress! Lets keep going...


### 1. why do we see this in the log? Are we running specialists twice, just for the heck of it :-)?
2025-07-16 07:08:00,569 - INFO - Successfully extracted 23 skills
2025-07-16 07:08:00,569 - INFO - Successfully extracted 23 skills

### 2. We should not use fallbacks. lets remove this one too:
```
Processing: location validation fallback
```

### 3. Lets add a horizontal line before we start processing a new job - clearer on screen

### 4. we wanted to extract one job, not three. Lets revise how we pass a number of jobs to the pipeline.

### 5. lets find out, `what daily_report_pipeline/specialists` are actually called in the pipeline. Once we know, lets move all others `to daily_report_pipeline/specialists/_archived_specialists`

### 6. We create `debug_raw_response_*.txt` in the project root. Lets put them in `debug/daily_report_pipeline_v7` instead. 

### 7. We have a problem with German job description. In these cases, we get `ERROR - No skills extracted from response`.  Lets use the logic in `0_mailboxes/sandy/inbox/strategos_sandy_translate_if_needed.md` to create a specialist and integrate that into the pipeline.

### 8. We never use JSON to extract from Ollama responses. We always use templates.

### 9. What is wrong with our codebase? Why are we having so many problems nnow? We didnt have them before, what did we do wrong? How can we improve?