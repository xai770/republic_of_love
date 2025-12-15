# Instruction Branching System Design

## Overview
The instruction branching system enables **conditional workflow execution** where the next step in a recipe depends on the outcome of the current step. This transforms recipes from linear sequences into intelligent decision trees.

## 🌳 **Branching Architecture**

### **Core Tables**
1. **`instructions`** - Enhanced with actor_id, timeout, and resource requirements
2. **`instruction_branches`** - Defines conditional logic and next steps
3. **`instruction_branch_executions`** - Tracks which branches were evaluated and taken

### **Branching Flow**
```
Execute Instruction → Evaluate Branches → Choose Next Step → Continue Recipe
       ↓                    ↓                  ↓
   Get Response      Check Conditions    Branch or Sequential
```

## 🎯 **Condition Types Supported**

### **1. Pattern Match (`pattern_match`)**
**Purpose:** Text/regex pattern matching in responses
```sql
condition_type = 'pattern_match'
condition_operator = 'regex_match' 
condition_value = '(error|failed|unable)'
```
**Use Cases:** Error detection, keyword presence, format validation

### **2. Length Check (`length_check`)**  
**Purpose:** Response length validation
```sql
condition_type = 'length_check'
condition_operator = 'less_than'
condition_value = '100'
```
**Use Cases:** Ensuring detailed responses, detecting incomplete answers

### **3. AI Evaluation (`ai_evaluation`)**
**Purpose:** Use another AI model to evaluate response quality
```sql
condition_type = 'ai_evaluation'  
condition_operator = 'greater_equal'
condition_value = '7'
branch_metadata = '{"evaluator_actor": "qwen3:latest", "eval_prompt": "Rate 1-10"}'
```
**Use Cases:** Quality assessment, sentiment analysis, complexity evaluation

### **4. Human Decision (`human_decision`)**
**Purpose:** Human actor chooses the branch (future implementation)
```sql
condition_type = 'human_decision'
condition_operator = 'user_choice'
condition_value = 'approve|reject|revise'
```
**Use Cases:** Quality control, creative approval, strategic decisions

### **5. Default Branch (`default`)**
**Purpose:** Fallback when no other conditions match
```sql
condition_type = 'default'
condition_operator = 'always' 
condition_value = 'true'
```
**Use Cases:** Ensures recipe continues even if all specific conditions fail

## 🔄 **Branch Actions**

### **Branch Action Types:**
- **`CONTINUE`** - Proceed to specified next_step_id
- **`ERROR_HANDLER`** - Route to error handling instruction
- **`REQUEST_MORE_DETAIL`** - Retry current instruction with additional prompt
- **`QUALITY_APPROVED`** - Mark as approved and continue
- **`HUMAN_REVIEW`** - Queue for human evaluation
- **`RETRY_WITH_DIFFERENT_ACTOR`** - Try same instruction with different AI model
- **`SKIP_TO_END`** - Jump to final step (early termination)
- **`DEFAULT_CONTINUE`** - Standard sequential progression

### **Special Branch Behaviors:**
- **`next_step_id = NULL`** - Repeat current instruction (with modified prompt)
- **`next_step_id = -1`** - End recipe execution
- **`next_step_id = 0`** - Go to recipe completion step

## ⚙️ **RecipeRunTestRunner Integration**

### **Enhanced Execution Algorithm:**
```python
def execute_recipe_with_branching(self, recipe_run_id):
    """Execute recipe with conditional branching support"""
    
    current_instruction_id = self.get_first_instruction(recipe_run_id)
    
    while current_instruction_id:
        # Execute current instruction
        instruction_run_id = self.execute_instruction(recipe_run_id, current_instruction_id)
        
        # Evaluate branches for this instruction
        next_instruction_id = self.evaluate_branches(recipe_run_id, instruction_run_id, current_instruction_id)
        
        # Handle special branch actions
        if next_instruction_id == -1:
            break  # End recipe
        elif next_instruction_id == None:
            continue  # Retry current instruction
        
        current_instruction_id = next_instruction_id
        
    self.complete_recipe_run(recipe_run_id)
```

### **Branch Evaluation Logic:**
```python
def evaluate_branches(self, recipe_run_id, instruction_run_id, instruction_id):
    """Evaluate branches in priority order"""
    
    branches = self.get_instruction_branches(instruction_id)  # Ordered by priority
    response = self.get_instruction_response(instruction_run_id)
    
    for branch in branches:
        condition_result = self.evaluate_condition(branch, response)
        
        # Log evaluation for debugging
        self.log_branch_evaluation(recipe_run_id, instruction_run_id, branch, condition_result)
        
        if condition_result['matches']:
            self.log_branch_taken(recipe_run_id, instruction_run_id, branch['branch_id'])
            return branch['next_step_id']
    
    # No branches matched - use sequential progression
    return self.get_next_sequential_instruction(instruction_id)
```

## 📊 **Example Branching Scenario**

### **Recipe: "Creative Writing with Quality Control"**

```sql
-- Step 1: Generate creative story (instruction_id = 100)
INSERT INTO instructions VALUES (100, 1, 1, 'Generate Story', 'Write a creative story about {topic}', null, null, null, now(), 1, 'llama3.2:latest', 300);

-- Step 2: Quality evaluation (instruction_id = 101)  
INSERT INTO instructions VALUES (101, 1, 2, 'Evaluate Quality', 'Rate this story quality 1-10 and explain why: {step1_response}', null, null, null, now(), 1, 'qwen3:latest', 180);

-- Step 3: Human review (instruction_id = 102)
INSERT INTO instructions VALUES (102, 1, 3, 'Human Review', 'Please review this story and provide feedback: {step1_response}', null, null, null, now(), 1, 'xai', 86400); -- 24 hour timeout

-- Step 4: Revision (instruction_id = 103)
INSERT INTO instructions VALUES (103, 1, 4, 'Revise Story', 'Revise the story based on this feedback: {step3_response}\n\nOriginal story: {step1_response}', null, null, null, now(), 1, 'llama3.2:latest', 300);
```

### **Branching Logic:**
```sql
-- From Step 1: Story generation
-- If story is too short, ask for more detail
INSERT INTO instruction_branches VALUES (1, 100, 'story_too_short', 100, 'REQUEST_MORE_DETAIL', '{"min_length": 200, "retry_suffix": "Please write a longer, more detailed story."}', 'length_check', 'less_than', '200', 1, 1);

-- If story contains inappropriate content, end recipe  
INSERT INTO instruction_branches VALUES (2, 100, 'inappropriate_content', -1, 'END_RECIPE', '{"pattern": "(violence|inappropriate)"}', 'pattern_match', 'regex_match', '(violence|inappropriate)', 2, 1);

-- If story is good quality, skip human review and go to completion
INSERT INTO instruction_branches VALUES (3, 100, 'high_quality_story', -1, 'QUALITY_APPROVED', '{"evaluator_actor": "qwen3:latest", "eval_prompt": "Rate story quality 1-10", "threshold": 8}', 'ai_evaluation', 'greater_equal', '8', 3, 1);

-- Default: proceed to quality evaluation
INSERT INTO instruction_branches VALUES (4, 100, 'default_evaluation', 101, 'DEFAULT_CONTINUE', '{}', 'default', 'always', 'true', 999, 1);

-- From Step 2: Quality evaluation  
-- If quality is low, go to human review
INSERT INTO instruction_branches VALUES (5, 101, 'low_quality', 102, 'HUMAN_REVIEW_NEEDED', '{"quality_threshold": 6}', 'ai_evaluation', 'less_than', '6', 1, 1);

-- If quality is good, end recipe successfully
INSERT INTO instruction_branches VALUES (6, 101, 'good_quality', -1, 'QUALITY_APPROVED', '{}', 'ai_evaluation', 'greater_equal', '6', 2, 1);
```

## 🎛️ **Branch Priority System**

**Priority Ordering (1 = highest priority):**
1. **Error Conditions** (priority 1-10) - Handle failures first
2. **Quality Gates** (priority 11-50) - Quality control checks  
3. **Flow Control** (priority 51-100) - Normal workflow decisions
4. **Default Actions** (priority 900+) - Fallback behaviors

**Evaluation Process:**
1. Get all branches for instruction ordered by `branch_priority ASC`
2. Evaluate conditions in priority order
3. Take first branch where condition evaluates to `true`
4. If no branches match, continue sequentially

## 📈 **Advanced Features**

### **1. Retry Logic with Different Actors**
```sql
-- If AI model fails, try with different model
INSERT INTO instruction_branches VALUES (7, 100, 'model_timeout', 100, 'RETRY_DIFFERENT_ACTOR', 
    '{"alternative_actor": "dolphin3:latest", "max_retries": 2}', 
    'execution_timeout', 'equals', 'true', 5, 1);
```

### **2. Dynamic Prompt Modification**
```sql  
-- If response lacks detail, retry with enhanced prompt
INSERT INTO instruction_branches VALUES (8, 100, 'enhance_prompt', 100, 'ENHANCE_PROMPT',
    '{"prompt_enhancement": "Be more specific and provide examples."}',
    'length_check', 'less_than', '150', 3, 1);
```

### **3. Multi-Condition Branching** (Future Enhancement)
```sql
-- Complex conditions: (length > 100) AND (quality > 7) AND (no_errors)
-- Would require condition_logic field: "length_check AND ai_evaluation AND pattern_match"
```

## 🛠️ **Implementation Phases**

### **Phase 1: Basic Branching (Current)**
- ✅ Pattern matching conditions
- ✅ Length check conditions  
- ✅ Default fallback branches
- ✅ Branch execution tracking

### **Phase 2: AI Evaluation Branching**
- 🔄 Implement AI evaluator actors
- 🔄 Response quality scoring
- 🔄 Sentiment analysis branching

### **Phase 3: Human Integration**  
- ⏳ Email notification system
- ⏳ Web interface for human decisions
- ⏳ Timeout and escalation handling

### **Phase 4: Advanced Logic**
- ⏳ Multi-condition branching (AND/OR logic)
- ⏳ Dynamic actor selection based on workload
- ⏳ Machine learning condition optimization

## 🎯 **Benefits of Branching System**

1. **Intelligent Workflows** - Recipes adapt based on actual outcomes
2. **Quality Control** - Automatic detection and handling of poor responses  
3. **Error Recovery** - Graceful handling of failures and timeouts
4. **Human Integration** - Seamless mixing of AI and human decision points
5. **Flexibility** - Same recipe can handle multiple scenarios dynamically
6. **Debugging** - Full branch evaluation history for troubleshooting

**This branching system transforms static recipes into intelligent, adaptive workflows! 🚀**