import re
import os
import glob

def _match_key(text):
    return re.sub(r'\s+', '', text).translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ))

def parse_mock_txt_files(directory):
    questions = []
    explanations = {}
    
    for filepath in glob.glob(os.path.join(directory, '*_解析版.txt')):
        filename = os.path.basename(filepath)
        category = "模擬試題" 
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split by question numbers roughly: "\n1. ", "\n2. "
        # First ensure we have a newline at the start
        content = "\n" + content
        blocks = re.split(r'\n(?=\d+\.\s)', content)
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            q_match = re.search(r'^(\d+)\.\s+(.*?)\n([A-D])\.', block, re.DOTALL)
            if not q_match:
                continue
            
            q_num = q_match.group(1)
            q_text = q_match.group(2).strip()
            
            options = {}
            for opt in ['A', 'B', 'C', 'D']:
                opt_match = re.search(fr'^{opt}\.\s+(.*?)(?=\n[A-D]\.|\n(?:解答|【正確答案】))', block, re.MULTILINE | re.DOTALL)
                if opt_match:
                    options[opt] = opt_match.group(1).strip()
            
            ans_match = re.search(r'(?:解答|【正確答案】)[：\s]*([A-D])', block)
            answer = ans_match.group(1) if ans_match else ""
            
            exp_match = re.search(r'(?:解析|【解析】)[：\n]*(.*)', block, re.DOTALL)
            explanation = exp_match.group(1).strip() if exp_match else ""
            
            q_obj = {
                'id': f"{filename}_{q_num}",
                'category': category,
                'source': filename,
                'number': q_num,
                'answer': answer,
                'question': q_text,
                'options': options
            }
            if answer and len(options) == 4:
                questions.append(q_obj)
            
            if explanation:
                key = _match_key(q_text)[:22]
                explanations[key] = (explanation, None)
                
    return questions, explanations

if __name__ == "__main__":
    d = r"C:\Users\f1e2n\Desktop\📁 我的專案\iPAS\同學分享"
    q, e = parse_mock_txt_files(d)
    print(f"Parsed {len(q)} questions and {len(e)} explanations.")
    if q:
        print("Sample question:", q[0])
        print("Sample explanation:", e[list(e.keys())[0]])
