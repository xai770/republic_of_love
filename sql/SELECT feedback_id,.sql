SELECT feedback_id,
       user_id,
       url,
       description,
       category,
       screenshot,
       annotation,
       viewport,
       user_agent,
       status,
       admin_notes,
       created_at,
       resolved_at

FROM public.feedback
WHERE status = 'open';