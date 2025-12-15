# Grader Model Recommendations
## Analysis Date: 2025-10-21

Based on 625 joke classification tests, here are the best alternative graders to gemma3:1b:

## 🏆 Top Recommendations

### 1. **llama3.2:latest** ⭐ BEST OVERALL
- **Speed**: 318ms avg (very fast!)
- **Accuracy**: 100% success rate, 100% joke recognition
- **Style**: 😊 LENIENT (recognizes jokes)
- **Quality Distribution**: 5 EXCELLENT, 13 GOOD, 6 MEDIOCRE, 1 BAD
- **Grader Score**: 31.43 (highest)
- **Why**: Fast, accurate, and gives fair ratings. Not overly harsh.

### 2. **llama3.2:1b** ⭐ FASTEST + FAIR
- **Speed**: 315ms avg (fastest!)
- **Accuracy**: 100% success rate, 92% joke recognition
- **Style**: 😊 LENIENT
- **Quality Distribution**: 8 EXCELLENT, 12 GOOD, 0 MEDIOCRE, 5 BAD
- **Grader Score**: 29.18
- **Why**: Fastest grader with excellent judgment. Slightly less recognition than :latest but more generous with ratings.

### 3. **granite3.1-moe:3b** ⭐ MOST GENEROUS
- **Speed**: 497ms avg (still fast)
- **Accuracy**: 100% success rate, 100% joke recognition
- **Style**: 😊 LENIENT
- **Quality Distribution**: 18 EXCELLENT!, 6 GOOD, 0 MEDIOCRE, 1 BAD
- **Grader Score**: 20.1
- **Why**: Gives the most EXCELLENT ratings (18/25). Very encouraging grader! Great if you want to see which jokes are actually decent.

### 4. **mistral:latest** - Good Balance
- **Speed**: 714ms avg
- **Accuracy**: 100% success rate, 100% joke recognition
- **Style**: 😊 LENIENT
- **Quality Distribution**: 0 EXCELLENT, 7 GOOD, 15 MEDIOCRE, 0 BAD
- **Why**: Spreads ratings more evenly. Good for nuanced evaluation.

## ⚖️ Balanced Graders (If You Want Middle Ground)

### **qwen2.5vl:latest**
- Speed: 781ms, Style: 😐 BALANCED (80% yes rate)
- More critical than llama but faster than gemma2

### **qwen2.5:7b**
- Speed: 811ms, Style: 😐 BALANCED (76% yes rate)
- Similar to qwen2.5vl but slightly stricter

## 🔍 Comparison: Current vs Recommended

| Metric | gemma3:1b (current) | llama3.2:latest (recommended) | granite3.1-moe:3b (generous) |
|--------|---------------------|-------------------------------|------------------------------|
| Speed | 390ms ⚡ | 318ms ⚡⚡ | 497ms ⚡ |
| Joke Recognition | 56% 😤 STRICT | 100% 😊 LENIENT | 100% 😊 LENIENT |
| EXCELLENT ratings | 0 | 5 | 18 🌟 |
| GOOD ratings | 0 | 13 | 6 |
| MEDIOCRE ratings | 25 | 6 | 0 |
| BAD ratings | 0 | 1 | 1 |
| Overall Style | All MEDIOCRE | Fair spread | Very generous |

## 🎯 Recommendation by Use Case

### **For Production Testing** → llama3.2:latest
- Fastest + most accurate
- Fair but not overly harsh
- Good spread of ratings

### **To Boost Model Morale** → granite3.1-moe:3b
- Gives generous ratings (18 EXCELLENT!)
- Still fast and reliable
- Good for seeing which jokes have potential

### **For Strictest Evaluation** → Keep gemma3:1b
- Most critical grader
- But be aware: it rated 0% of generated jokes as "IS_JOKE: YES"

### **For Speed-Critical Tests** → llama3.2:1b
- Absolute fastest (315ms)
- Still fair and accurate
- Smallest model but excellent performance

## 🚫 Models to AVOID as Graders

1. **codegemma:2b** - Too strict (only 33% recognition), inconsistent
2. **qwen3:latest** - Too slow (19.7 seconds!), times out frequently
3. **phi4-mini-reasoning:latest** - Very slow (14.7s), defeats purpose of grading
4. **qwen3:4b** - Slow (10.7s) with frequent timeouts

## 💡 Next Steps

### Option 1: Rerun with Better Grader
```sql
-- Create new recipes using llama3.2:latest as grader in session 2
-- Keep session 1 (generation) the same, just swap session 2 grader
```

### Option 2: Run Parallel Grading
```sql
-- Grade existing jokes with multiple graders to compare
-- Use session context passing to feed existing jokes to new graders
```

### Option 3: Multi-Grader Consensus
```sql
-- Have 3 graders score each joke
-- Take average or majority vote
-- Recommended: llama3.2:latest + granite3.1-moe:3b + qwen2.5vl:latest
```

## 📊 Key Insight

**gemma3:1b is an outlier grader**:
- Only 56% joke recognition (vs 80-100% for others)
- Gives ALL MEDIOCRE ratings (never EXCELLENT/GOOD/BAD)
- This explains why ALL generated jokes got "IS_JOKE: NO" - it's just very strict!

**Reality check**: The pre-written jokes got 79% "IS_JOKE: YES" across all models. This suggests the AI-generated jokes ARE significantly worse quality, but gemma3:1b is also harsher than necessary.

**Best approach**: Rerun with **llama3.2:latest** as grader - it's faster, more accurate, and will give you a realistic spread of ratings to identify which models actually generate decent jokes.
