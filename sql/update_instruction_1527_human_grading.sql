-- Update instruction 1527 for human grading with improved rubric
UPDATE instructions 
SET 
    actor_id = 'xai',
    timeout_seconds = 86400,  -- 24 hour timeout for human grading
    prompt_template = '## Human Grading Instructions
You are grading a model''s response to a cross-domain integration challenge. 

## Original Challenge and Model Response:
CHALLENGE: Generate an integration strategy combining cooking and chemistry
STRATEGY TO EVALUATE:
{step1_response}

## PRECISE Grading Rubric
Count ONLY mechanisms that have ALL THREE components:
1. Names a specific technique/method/process  
2. Explains HOW the two domains connect through this technique
3. Describes a concrete outcome or application

EXAMPLES of Valid Mechanisms:
- "pH testing in bread making: Use chemistry pH meters to monitor dough acidity, resulting in consistent texture control"
- "Molecular gastronomy spherification: Apply calcium chloride chemistry to create caviar-like food textures"

INVALID Examples (don''t count):
- "Chemistry helps cooking" (too vague)
- "Use temperature control" (no explanation of HOW)  
- "Food safety is important" (no specific mechanism)

## STRICT Grading Scale
[A] Excellent: 3 or more valid mechanisms (by definition above)
[B] Good: Exactly 2 valid mechanisms  
[C] Acceptable: Exactly 1 valid mechanism
[D] Poor: Attempts integration but 0 valid mechanisms (too vague)
[F] Fail: No integration attempted or nonsensical

## Your Task
1. Read the strategy carefully
2. Identify potential mechanisms  
3. Check each mechanism against the 3-component definition
4. Count ONLY mechanisms that meet all 3 components
5. Assign grade based on count

Respond with your grade: A, B, C, D, or F'
WHERE instruction_id = 1527;