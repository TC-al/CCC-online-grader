import time
from flask import Flask, render_template, request, jsonify
import subprocess, tempfile, os, random, json, io, sys, traceback, concurrent.futures, shutil, string

app = Flask(__name__)

#########################
# Compilation and Running Functions for Each Language
#########################

# -- Java --
def compile_java_code(code):
    tmpdirname = tempfile.mkdtemp()
    filepath = os.path.join(tmpdirname, "Solution.java")
    with open(filepath, "w") as f:
        f.write(code)
    compile_proc = subprocess.run(
        ["javac", "Solution.java"],
        cwd=tmpdirname,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if compile_proc.returncode != 0:
        shutil.rmtree(tmpdirname, ignore_errors=True)
        return None, f"Compilation Error:\n{compile_proc.stderr}"
    return tmpdirname, None

def run_java_executable(tmpdirname, input_data):
    run_proc = subprocess.run(
        ["java", "Solution"],
        cwd=tmpdirname,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if run_proc.returncode != 0:
        return None, f"Runtime Error:\n{run_proc.stderr}"
    return run_proc.stdout.strip(), None

# -- Python --
def run_python_code_once(code, input_data):
    old_stdout = sys.stdout
    old_stdin = sys.stdin
    try:
        sys.stdout = io.StringIO()
        sys.stdin = io.StringIO(input_data)
        local_vars = {}
        exec(code, {}, local_vars)
        output = sys.stdout.getvalue().strip()
        return output, None
    except Exception:
        error = traceback.format_exc()
        return None, f"Error during execution:\n{error}"
    finally:
        sys.stdout = old_stdout
        sys.stdin = old_stdin

# -- JavaScript --
def run_javascript_code(code, input_data):
    tmpdirname = tempfile.mkdtemp()
    filepath = os.path.join(tmpdirname, "solution.js")
    with open(filepath, "w") as f:
        f.write(code)
    run_proc = subprocess.run(
        ["node", "solution.js"],
        cwd=tmpdirname,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    shutil.rmtree(tmpdirname, ignore_errors=True)
    if run_proc.returncode != 0:
        return None, f"Runtime Error:\n{run_proc.stderr}"
    return run_proc.stdout.strip(), None

#########################
# Helper for Bronze Problem
#########################
def compute_bronze_result(scores):
    distinct = sorted(set(scores), reverse=True)
    bronze = distinct[2]
    count = scores.count(bronze)
    return bronze, count

def generate_bronze_test():
    while True:
        N = random.randint(3, 20)
        scores = [random.randint(0, 75) for _ in range(N)]
        if len(set(scores)) >= 3:
            break
    input_data = str(N) + "\n" + "\n".join(str(s) for s in scores) + "\n"
    bronze, count = compute_bronze_result(scores)
    expected = f"{bronze} {count}"
    return input_data, expected

#########################
# Helper for Troublesome Keys Problem
#########################
def generate_troublesome_test():
    # Choose a random length between 5 and 15.
    N = random.randint(5, 15)
    # Pick a silly key
    silly = random.choice(string.ascii_lowercase)
    # Pick a wrong letter different from the silly key.
    wrong = random.choice([c for c in string.ascii_lowercase if c != silly])
    # Decide randomly whether the quiet key is pressed.
    quiet_pressed = random.choice([True, False])
    if quiet_pressed:
        quiet = random.choice([c for c in string.ascii_lowercase if c != silly])
    else:
        quiet = None
    # Generate an array of keys of length N.
    keys = [random.choice(string.ascii_lowercase) for _ in range(N)]
    # Force at least one occurrence of the silly key.
    pos_silly = random.randint(0, N-1)
    keys[pos_silly] = silly
    # If quiet key is to be pressed, force at least one occurrence in a non-adjacent position.
    if quiet_pressed:
        possible_positions = [i for i in range(N) if abs(i - pos_silly) > 1]
        if not possible_positions:
            possible_positions = [i for i in range(N) if i != pos_silly]
        pos_quiet = random.choice(possible_positions)
        keys[pos_quiet] = quiet
    input_line = "".join(keys)
    # Generate displayed output.
    displayed = []
    for k in keys:
        if quiet_pressed and quiet is not None and k == quiet:
            continue
        elif k == silly:
            displayed.append(wrong)
        else:
            displayed.append(k)
    output_line = "".join(displayed)
    expected = f"{silly} {wrong}\n" + (quiet if quiet_pressed else "-")
    test_input = input_line + "\n" + output_line + "\n"
    return test_input, expected

#########################
# Routes
#########################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def run_code():
    code = request.form.get('code')
    language = request.form.get('language')
    problem = request.form.get('problem', 'default')
    
    if problem == "dusa":
        test = {"input": "5\n3\n2\n9\n20\n22\n14\n", "expected": "19"}
    elif problem == "bronze":
        test = {"input": "4\n70\n62\n58\n73\n", "expected": "62 1"}
    elif problem == "troublesome":
        input_data, expected = generate_troublesome_test()
        test = {"input": input_data, "expected": expected}
    else:
        test = {"input": "0\n2\n4\n", "expected": "28"}
        
    start_time = time.time()
    if language == "java":
        tmpdirname, compile_err = compile_java_code(code)
        if compile_err:
            runtime = round((time.time() - start_time)*1000, 2)
            return jsonify({
                "results": [{
                    "test_case": 1,
                    "input": test["input"],
                    "expected": test["expected"],
                    "output": compile_err,
                    "passed": False,
                    "runtime": runtime
                }],
                "all_passed": False
            })
        output, run_err = run_java_executable(tmpdirname, test["input"])
        shutil.rmtree(tmpdirname, ignore_errors=True)
        runtime = round((time.time() - start_time)*1000, 2)
        if run_err:
            passed = False
            final_output = run_err
        else:
            passed = (output == test["expected"])
            final_output = output
    elif language == "javascript":
        output, run_err = run_javascript_code(code, test["input"])
        runtime = round((time.time() - start_time)*1000, 2)
        if run_err:
            passed = False
            final_output = run_err
        else:
            passed = (output == test["expected"])
            final_output = output
    elif language == "python":
        output, run_err = run_python_code_once(code, test["input"])
        runtime = round((time.time() - start_time)*1000, 2)
        if run_err:
            passed = False
            final_output = run_err
        else:
            passed = (output == test["expected"])
            final_output = output
    else:
        return jsonify({"error": "Unsupported language"}), 400

    return jsonify({
        "results": [{
            "test_case": 1,
            "input": test["input"],
            "expected": test["expected"],
            "output": final_output,
            "passed": passed,
            "runtime": runtime
        }],
        "all_passed": passed
    })

@app.route('/submit', methods=['POST'])
def submit_code():
    code = request.form.get('code')
    language = request.form.get('language')
    problem = request.form.get('problem', 'default')
    
    # Lower test count for non-default problems
    total = 100 if problem == "default" else 50

    tmpdirname = None
    compile_err = None
    if language == "java":
        tmpdirname, compile_err = compile_java_code(code)
    
    # Pre-generate test cases.
    test_cases = []
    if problem == "dusa":
        for _ in range(total):
            initial = random.randint(1, 50)
            D = initial
            yobi_list = []
            while True:
                y = random.randint(1, 50)
                yobi_list.append(y)
                if y >= D:
                    break
                else:
                    D += y
            input_data = str(initial) + "\n" + "\n".join(str(y) for y in yobi_list) + "\n"
            expected = str(D)
            test_cases.append((input_data, expected))
    elif problem == "bronze":
        for _ in range(total):
            input_data, expected = generate_bronze_test()
            test_cases.append((input_data, expected))
    elif problem == "troublesome":
        for _ in range(total):
            input_data, expected = generate_troublesome_test()
            test_cases.append((input_data, expected))
    else:
        for _ in range(total):
            R = random.randint(0, 100)
            G = random.randint(0, 100)
            B = random.randint(0, 100)
            input_data = f"{R}\n{G}\n{B}\n"
            expected = str(R*3 + G*4 + B*5)
            test_cases.append((input_data, expected))
    
    def run_test(i):
        if compile_err is not None:
            return {
                "test_case": i+1,
                "input": "",
                "expected": "",
                "output": compile_err,
                "passed": False,
                "runtime": 0
            }
        input_data, expected = test_cases[i]
        start_time = time.time()
        if language == "java":
            output, run_err = run_java_executable(tmpdirname, input_data)
        elif language == "javascript":
            output, run_err = run_javascript_code(code, input_data)
        elif language == "python":
            output, run_err = run_python_code_once(code, input_data)
        else:
            output, run_err = ("", "Unsupported language")
        runtime = round((time.time() - start_time)*1000, 2)
        if run_err:
            return {
                "test_case": i+1,
                "input": input_data,
                "expected": expected,
                "output": run_err,
                "passed": False,
                "runtime": runtime
            }
        passed = (output == expected)
        return {
            "test_case": i+1,
            "input": input_data,
            "expected": expected,
            "output": output,
            "passed": passed,
            "runtime": runtime
        }
    
    def generate():
        overall_start = time.time()
        completed = 0
        passed_count = 0
        failed_count = 0

        # Process tests sequentially with a simple loop for streaming progress.
        for i in range(total):
            result = run_test(i)
            completed += 1
            if result["passed"]:
                passed_count += 1
            else:
                failed_count += 1
                yield json.dumps({"type": "failed", **result}) + "\n"
            yield json.dumps({"type": "progress", "completed": completed, "total": total}) + "\n"
        if tmpdirname is not None:
            shutil.rmtree(tmpdirname, ignore_errors=True)
        overall_end = time.time()
        elapsed_ms = (overall_end - overall_start) * 1000
        avg_runtime = round(elapsed_ms / total, 2)
        final_status = "Passed" if failed_count == 0 else "Failed"
        yield json.dumps({
            "type": "summary",
            "final_status": final_status,
            "avg_runtime": avg_runtime,
            "passed_count": passed_count,
            "failed_count": failed_count
        }) + "\n"
    
    return app.response_class(generate(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)
