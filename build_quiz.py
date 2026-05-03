import os
import re
import json
import glob

def normalize_text(text):
    return text.translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ))

def parse_files(directory):
    questions = []
    
    # regex matches: (Answer) (Number). (Question Text)
    # Answer can be A, B, C, D (full width or half width)
    re_question_start = re.compile(r'^([A-Da-d])\s+(\d+)\.\s+(.*)')
    # Match option start: (A), （A）, A., A、 etc.
    re_option = re.compile(r'^[\(（]?([A-Da-d])[\)）\.\、]\s*(.*)')
    
    # We also need to ignore headers/footers
    re_ignore = re.compile(r'^(===|11[45]\s*年|第一科|第二科|考試日期|第\s*\d+\s*頁|答案\s*題\s*目|一、選擇題)')

    for filepath in glob.glob(os.path.join(directory, '*.txt')):
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        current_q = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if re_ignore.search(line):
                continue
                
            norm_line = normalize_text(line)
            
            q_match = re_question_start.match(norm_line)
            if q_match:
                if current_q and current_q.get('options') and len(current_q['options']) > 0:
                    questions.append(current_q)
                
                ans = q_match.group(1).upper()
                q_num = q_match.group(2)
                q_text = q_match.group(3).strip()
                
                current_q = {
                    'source': filename,
                    'number': q_num,
                    'answer': ans,
                    'question': q_text,
                    'options': {}
                }
                continue
                
            opt_match = re_option.match(norm_line)
            if opt_match and current_q:
                opt_key = opt_match.group(1).upper()
                opt_text = opt_match.group(2).strip()
                # Clean up trailing semicolons if present
                if opt_text.endswith('；'):
                    opt_text = opt_text[:-1]
                current_q['options'][opt_key] = opt_text
                continue
                
            # If it's neither a new question nor an option, it might be a continuation of the previous text
            if current_q:
                # If we haven't started options yet, it's a continuation of the question
                if not current_q['options']:
                    current_q['question'] += '\n' + line
                else:
                    # It's a continuation of the last option
                    last_opt = list(current_q['options'].keys())[-1]
                    additional_text = line
                    if additional_text.endswith('；'):
                        additional_text = additional_text[:-1]
                    current_q['options'][last_opt] += '\n' + additional_text
                    
        # Add the last question
        if current_q and current_q.get('options') and len(current_q['options']) > 0:
            questions.append(current_q)
            
    return questions

def build_html(questions, output_file):
    html_template = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iPAS AI 應用規劃師 - 刷題神器</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js"></script>
    <style>
        body { background-color: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .fade-enter-active, .fade-leave-active { transition: opacity .3s; }
        .fade-enter, .fade-leave-to { opacity: 0; }
        .option-btn { transition: all 0.2s; white-space: pre-wrap; text-align: left;}
        .option-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    </style>
</head>
<body class="text-gray-800">
    <div id="app" class="min-h-screen flex flex-col max-w-4xl mx-auto p-4 md:p-8">
        <header class="mb-8 flex justify-between items-end border-b pb-4">
            <div>
                <h1 class="text-3xl font-bold text-indigo-700">iPAS AI 刷題神器</h1>
                <p class="text-sm text-gray-500 mt-1">共 {{ questions.length }} 題 | 目前分類：{{ currentMode === 'all' ? '全部題庫' : '錯題複習' }}</p>
            </div>
            <div class="text-right">
                <p class="text-lg font-semibold text-green-600">正確: {{ correctCount }}</p>
                <p class="text-lg font-semibold text-red-600">錯誤: {{ wrongCount }}</p>
            </div>
        </header>

        <main class="flex-grow bg-white rounded-xl shadow-lg p-6 relative">
            <div v-if="questions.length === 0" class="text-center py-20 text-gray-500">
                沒有找到題目！
            </div>
            <div v-else-if="currentIndex >= workingQuestions.length" class="text-center py-20">
                <h2 class="text-2xl font-bold text-gray-700 mb-4">恭喜！已完成此模式所有題目</h2>
                <div class="space-x-4">
                    <button @click="resetQuiz" class="px-6 py-2 bg-indigo-600 text-white rounded shadow hover:bg-indigo-700">重新開始</button>
                    <button v-if="wrongQuestions.length > 0 && currentMode === 'all'" @click="startWrongMode" class="px-6 py-2 bg-red-500 text-white rounded shadow hover:bg-red-600">複習錯題 ({{ wrongQuestions.length }})</button>
                </div>
            </div>
            <div v-else class="flex flex-col h-full">
                <div class="mb-4 flex justify-between text-sm text-gray-500">
                    <span>進度: {{ currentIndex + 1 }} / {{ workingQuestions.length }}</span>
                    <span>來源: {{ currentQuestion.source }}</span>
                </div>
                
                <h2 class="text-xl md:text-2xl font-semibold mb-6 whitespace-pre-wrap leading-relaxed">{{ currentQuestion.number }}. {{ currentQuestion.question }}</h2>
                
                <div class="space-y-3 flex-grow">
                    <button 
                        v-for="(text, key) in currentQuestion.options" :key="key"
                        @click="selectOption(key)"
                        :disabled="hasAnswered"
                        :class="[
                            'w-full p-4 rounded-lg border-2 option-btn text-lg',
                            !hasAnswered ? 'border-gray-200 hover:border-indigo-400 bg-gray-50' : '',
                            hasAnswered && key === currentQuestion.answer ? 'border-green-500 bg-green-50 text-green-700 font-bold' : '',
                            hasAnswered && key === selectedAnswer && key !== currentQuestion.answer ? 'border-red-500 bg-red-50 text-red-700' : '',
                            hasAnswered && key !== selectedAnswer && key !== currentQuestion.answer ? 'border-gray-200 bg-gray-100 opacity-50' : ''
                        ]"
                    >
                        <span class="font-bold mr-2">({{ key }})</span> {{ text }}
                    </button>
                </div>

                <div class="mt-8 pt-4 border-t flex justify-between items-center h-16">
                    <div v-if="hasAnswered" class="text-lg font-bold">
                        <span v-if="isCorrect" class="text-green-600">✅ 答對了！</span>
                        <span v-else class="text-red-600">❌ 答錯了！正確答案是 ({{ currentQuestion.answer }})</span>
                    </div>
                    <div v-else></div>
                    
                    <button 
                        v-if="hasAnswered"
                        @click="nextQuestion"
                        class="px-8 py-3 bg-indigo-600 text-white font-bold rounded-lg shadow-md hover:bg-indigo-700 transition-colors"
                    >
                        下一題 ➔
                    </button>
                </div>
            </div>
        </main>
        
        <footer class="mt-8 text-center text-sm text-gray-400">
            可以隨時重新整理網頁，進度會重置。 <br>
            Made by Gemini
        </footer>
    </div>

    <script>
        const rawQuestions = {{QUESTIONS_JSON}};
        
        // Shuffle function
        function shuffle(array) {
            let currentIndex = array.length,  randomIndex;
            while (currentIndex != 0) {
                randomIndex = Math.floor(Math.random() * currentIndex);
                currentIndex--;
                [array[currentIndex], array[randomIndex]] = [array[randomIndex], array[currentIndex]];
            }
            return array;
        }

        new Vue({
            el: '#app',
            data: {
                questions: rawQuestions,
                workingQuestions: [],
                wrongQuestions: [],
                currentIndex: 0,
                selectedAnswer: null,
                hasAnswered: false,
                isCorrect: false,
                correctCount: 0,
                wrongCount: 0,
                currentMode: 'all' // 'all' or 'wrong'
            },
            computed: {
                currentQuestion() {
                    if (this.currentIndex < this.workingQuestions.length) {
                        return this.workingQuestions[this.currentIndex];
                    }
                    return null;
                }
            },
            created() {
                this.resetQuiz();
            },
            methods: {
                resetQuiz() {
                    this.workingQuestions = shuffle([...this.questions]);
                    this.currentIndex = 0;
                    this.correctCount = 0;
                    this.wrongCount = 0;
                    this.wrongQuestions = [];
                    this.currentMode = 'all';
                    this.resetTurn();
                },
                startWrongMode() {
                    this.workingQuestions = shuffle([...this.wrongQuestions]);
                    this.currentIndex = 0;
                    this.currentMode = 'wrong';
                    this.resetTurn();
                },
                resetTurn() {
                    this.selectedAnswer = null;
                    this.hasAnswered = false;
                    this.isCorrect = false;
                },
                selectOption(key) {
                    if (this.hasAnswered) return;
                    
                    this.selectedAnswer = key;
                    this.hasAnswered = true;
                    this.isCorrect = (key === this.currentQuestion.answer);
                    
                    if (this.isCorrect) {
                        this.correctCount++;
                    } else {
                        this.wrongCount++;
                        // Add to wrong questions if not already there
                        if (!this.wrongQuestions.some(q => q.question === this.currentQuestion.question)) {
                            this.wrongQuestions.push(this.currentQuestion);
                        }
                    }
                },
                nextQuestion() {
                    this.currentIndex++;
                    this.resetTurn();
                }
            }
        });
    </script>
</body>
</html>"""
    
    json_data = json.dumps(questions, ensure_ascii=False)
    html_content = html_template.replace('{{QUESTIONS_JSON}}', json_data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"成功生成刷題程式！包含 {len(questions)} 道題目。")
    print(f"請在瀏覽器中開啟: {output_file}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    past_exams_dir = os.path.join(script_dir, 'past_exams')
    output_html = os.path.join(script_dir, 'iPAS刷題神器.html')
    
    print(f"正在讀取目錄: {past_exams_dir}")
    questions = parse_files(past_exams_dir)
    build_html(questions, output_html)
