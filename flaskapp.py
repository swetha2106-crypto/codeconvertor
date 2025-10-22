# app.py
from flask import Flask, render_template, request, send_file
import io
import re

app = Flask(__name__)

languages = ["python", "java", "c", "c++", "c#", "javascript"]

# ---------------- ADVANCED FEATURE MAPPINGS ----------------
class CodeTranslator:
    def __init__(self, source_lang, target_lang):
        self.source_lang = source_lang.lower()
        self.target_lang = target_lang.lower()
        self.indent_level = 0
        self.in_function = False
        self.in_class = False
        
    def translate_line(self, line):
        stripped = line.strip()
        if not stripped:
            return ""

        # ---------------- COMMENTS ----------------
        if self.translate_comment(stripped):
            return self.translate_comment(stripped)

        # ---------------- IMPORTS ----------------
        if self.translate_import(stripped):
            return self.translate_import(stripped)

        # ---------------- PYTHON AS SOURCE ----------------
        if self.source_lang == "python":
            return self.from_python(stripped)

        # ---------------- JAVA AS SOURCE ----------------
        if self.source_lang == "java":
            return self.from_java(stripped)

        # ---------------- C# AS SOURCE ----------------
        if self.source_lang == "c#":
            return self.from_csharp(stripped)

        # ---------------- C / C++ AS SOURCE ----------------
        if self.source_lang in ["c", "c++"]:
            return self.from_c_cpp(stripped)

        # ---------------- JAVASCRIPT AS SOURCE ----------------
        if self.source_lang == "javascript":
            return self.from_javascript(stripped)

        return stripped

    # ---------------- COMMENT TRANSLATION ----------------
    def translate_comment(self, line):
        if line.startswith("#"):
            if self.target_lang in ["java", "c#", "c", "c++", "javascript"]:
                return "// " + line.lstrip("#").strip()
            return line
        if line.startswith("//"):
            if self.target_lang == "python":
                return "# " + line.lstrip("/").strip()
            return line
        if line.startswith("/*") or line.startswith("*/"):
            if self.target_lang == "python":
                return "# " + line.strip("/*").strip()
            return line
        return None

    # ---------------- IMPORT TRANSLATION ----------------
    def translate_import(self, line):
        # Python imports
        if line.startswith("import ") or line.startswith("from "):
            if self.target_lang == "java":
                module = line.split()[-1].strip(";")
                return f"import {module}.*;"
            if self.target_lang == "javascript":
                module = line.split()[-1]
                return f"const {module} = require('{module}');"
            if self.target_lang in ["c", "c++"]:
                return f"#include <{line.split()[-1]}>"
            return line
        
        # Java imports
        if line.startswith("import ") and line.endswith(";"):
            if self.target_lang == "python":
                module = line.split()[1].rstrip(";").split(".")[-1]
                return f"import {module}"
            return line
        
        # C/C++ includes
        if line.startswith("#include"):
            if self.target_lang == "python":
                return "# " + line
            return line
            
        return None

    # ---------------- FROM PYTHON ----------------
    def from_python(self, line):
        # PRINT with formatting
        if line.startswith("print("):
            content = self.extract_parentheses(line, "print")
            if self.target_lang in ["java", "c#"]:
                return f"System.out.println({content});"
            if self.target_lang in ["c", "c++"]:
                if '"' in content or "'" in content:
                    return f'printf({content});'
                return f'printf("%d\\n", {content});'
            if self.target_lang == "javascript":
                return f"console.log({content});"

        # FUNCTION DEFINITION with return type and parameters
        if line.startswith("def ") and ":" in line:
            match = re.match(r'def\s+(\w+)\s*\((.*?)\)\s*:', line)
            if match:
                name, params = match.groups()
                param_list = [p.strip() for p in params.split(",") if p.strip()]
                
                if self.target_lang in ["java", "c#"]:
                    typed_params = ", ".join([f"Object {p}" for p in param_list]) if param_list else ""
                    return f"public static Object {name}({typed_params}) {{"
                if self.target_lang in ["c", "c++"]:
                    typed_params = ", ".join([f"int {p}" for p in param_list]) if param_list else ""
                    return f"int {name}({typed_params}) {{"
                if self.target_lang == "javascript":
                    return f"function {name}({', '.join(param_list)}) {{"

        # RETURN statement
        if line.startswith("return "):
            value = line[7:].strip()
            if self.target_lang in ["java", "c#", "c", "c++", "javascript"]:
                return f"return {value};"
            return line

        # VARIABLE ASSIGNMENTS (including typed)
        if "=" in line and not any(line.startswith(x) for x in ["def ", "class ", "if ", "elif ", "else", "for ", "while "]):
            return self.translate_assignment(line)

        # CLASS DEFINITION
        if line.startswith("class ") and ":" in line:
            match = re.match(r'class\s+(\w+)(?:\((.*?)\))?\s*:', line)
            if match:
                name, parent = match.groups()
                if self.target_lang in ["java", "c#", "c++", "javascript"]:
                    if parent:
                        return f"class {name} extends {parent} {{"
                    return f"class {name} {{"

        # CONSTRUCTOR (__init__)
        if line.startswith("def __init__"):
            match = re.match(r'def\s+__init__\s*\(self,?\s*(.*?)\)\s*:', line)
            if match:
                params = match.group(1)
                if self.target_lang == "java":
                    return f"public {self.in_class}({params}) {{"
                if self.target_lang == "c#":
                    return f"public {self.in_class}({params}) {{"
                if self.target_lang == "c++":
                    return f"{self.in_class}({params}) {{"
                if self.target_lang == "javascript":
                    return f"constructor({params}) {{"

        # IF / ELIF / ELSE
        if line.startswith("if ") and ":" in line:
            cond = line[3:line.rfind(":")].strip()
            cond = self.translate_condition(cond)
            if self.target_lang in ["java", "c#", "c", "c++", "javascript"]:
                return f"if ({cond}) {{"
            
        if line.startswith("elif ") and ":" in line:
            cond = line[5:line.rfind(":")].strip()
            cond = self.translate_condition(cond)
            if self.target_lang in ["java", "c#", "c", "c++", "javascript"]:
                return f"}} else if ({cond}) {{"
            
        if line.startswith("else:"):
            if self.target_lang in ["java", "c#", "c", "c++", "javascript"]:
                return "} else {"

        # FOR LOOP (including range, enumerate)
        if line.startswith("for ") and ":" in line:
            return self.translate_for_loop(line)

        # WHILE LOOP
        if line.startswith("while ") and ":" in line:
            cond = line[6:line.rfind(":")].strip()
            cond = self.translate_condition(cond)
            if self.target_lang in ["java", "c#", "c", "c++", "javascript"]:
                return f"while ({cond}) {{"

        # TRY/EXCEPT/FINALLY
        if line.startswith("try:"):
            if self.target_lang in ["java", "c#", "javascript"]:
                return "try {"
            if self.target_lang in ["c", "c++"]:
                return "// try-catch not directly supported in C"
                
        if line.startswith("except"):
            match = re.match(r'except\s*(\w+)?\s*(?:as\s+(\w+))?:', line)
            if match and self.target_lang in ["java", "c#"]:
                exc_type = match.group(1) or "Exception"
                exc_var = match.group(2) or "e"
                return f"}} catch ({exc_type} {exc_var}) {{"
            if self.target_lang == "javascript":
                exc_var = match.group(2) if match else "e"
                return f"}} catch ({exc_var}) {{"
                
        if line.startswith("finally:"):
            if self.target_lang in ["java", "c#", "javascript"]:
                return "} finally {"

        # LIST/ARRAY OPERATIONS
        if ".append(" in line:
            return self.translate_append(line)
        
        if ".extend(" in line or ".remove(" in line or ".pop(" in line:
            return self.translate_list_operation(line)

        # DICTIONARY OPERATIONS
        if line.startswith("{") and ":" in line and "}" in line:
            return self.translate_dict(line)

        # STRING OPERATIONS
        if ".split(" in line or ".join(" in line or ".replace(" in line:
            return self.translate_string_operation(line)

        # LAMBDA FUNCTIONS
        if "lambda" in line:
            return self.translate_lambda(line)

        # LIST COMPREHENSION
        if "[" in line and "for" in line and "]" in line:
            return self.translate_list_comprehension(line)

        return line

    # ---------------- FROM JAVA ----------------
    def from_java(self, line):
        # Print statements
        if "System.out.println" in line or "System.out.print" in line:
            content = self.extract_parentheses(line, "System.out.print")
            if self.target_lang == "python":
                return f"print({content})"
            if self.target_lang in ["c", "c++"]:
                return f'printf({content});'
            if self.target_lang == "javascript":
                return f"console.log({content});"

        # Function/Method definition
        if re.match(r'(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(', line):
            if self.target_lang == "python":
                match = re.search(r'\w+\s+(\w+)\s*\((.*?)\)', line)
                if match:
                    name, params = match.groups()
                    param_list = [p.split()[-1] for p in params.split(",") if p.strip()]
                    return f"def {name}({', '.join(param_list)}):"

        # Variable declarations
        if re.match(r'(int|float|double|String|boolean|char)\s+\w+', line):
            return self.translate_java_variable(line)

        # Class definition
        if line.startswith("class ") or line.startswith("public class "):
            match = re.search(r'class\s+(\w+)', line)
            if match and self.target_lang == "python":
                return f"class {match.group(1)}:"

        # Control structures
        if line.startswith("if ") or line.startswith("} else if ") or line.startswith("else {"):
            return self.from_java_control(line)

        # For loop
        if line.startswith("for "):
            return self.from_java_for_loop(line)

        # Closing braces
        if line == "}" or line == "};":
            if self.target_lang == "python":
                return ""
            return line

        return line

    # ---------------- FROM C# ----------------
    def from_csharp(self, line):
        # Similar to Java with Console instead of System.out
        if "Console.WriteLine" in line or "Console.Write" in line:
            content = self.extract_parentheses(line, "Console.Write")
            if self.target_lang == "python":
                return f"print({content})"
            if self.target_lang == "java":
                return f"System.out.println({content});"
            if self.target_lang in ["c", "c++"]:
                return f'printf({content});'
            if self.target_lang == "javascript":
                return f"console.log({content});"
        
        # Rest similar to Java
        return self.from_java(line)

    # ---------------- FROM C/C++ ----------------
    def from_c_cpp(self, line):
        # Printf statements
        if "printf" in line:
            content = self.extract_parentheses(line, "printf")
            if self.target_lang == "python":
                # Simple conversion, may need refinement
                content = content.replace('"%d"', '').replace('"%s"', '').replace('\\n', '')
                return f"print({content.strip(', ')})"
            if self.target_lang == "java":
                return f"System.out.println({content});"
            if self.target_lang == "javascript":
                return f"console.log({content});"

        # Scanf statements
        if "scanf" in line:
            if self.target_lang == "python":
                return "# input() - translate manually"

        # Variable declarations
        if re.match(r'(int|float|double|char)\s+\w+', line):
            return self.translate_c_variable(line)

        # Pointers
        if "*" in line and re.match(r'(int|float|double|char)\s*\*', line):
            if self.target_lang == "python":
                return "# pointer - use object reference"

        # Struct
        if line.startswith("struct "):
            match = re.search(r'struct\s+(\w+)', line)
            if match and self.target_lang == "python":
                return f"class {match.group(1)}:"

        return line

    # ---------------- FROM JAVASCRIPT ----------------
    def from_javascript(self, line):
        # Console.log
        if "console.log" in line:
            content = self.extract_parentheses(line, "console.log")
            if self.target_lang == "python":
                return f"print({content})"
            if self.target_lang == "java":
                return f"System.out.println({content});"
            if self.target_lang in ["c", "c++"]:
                return f'printf({content});'

        # Function definitions
        if line.startswith("function "):
            match = re.match(r'function\s+(\w+)\s*\((.*?)\)', line)
            if match:
                name, params = match.groups()
                if self.target_lang == "python":
                    return f"def {name}({params}):"
                if self.target_lang in ["java", "c#"]:
                    return f"public static void {name}({params}) {{"

        # Arrow functions
        if "=>" in line:
            return self.translate_arrow_function(line)

        # Variable declarations
        if line.startswith("let ") or line.startswith("const ") or line.startswith("var "):
            return self.translate_js_variable(line)

        # Array methods
        if ".push(" in line or ".pop(" in line or ".shift(" in line:
            return self.translate_js_array_method(line)

        return line

    # ---------------- HELPER FUNCTIONS ----------------
    def extract_parentheses(self, line, prefix):
        start = line.find(prefix) + len(prefix)
        paren_start = line.find("(", start)
        if paren_start == -1:
            return ""
        depth = 1
        i = paren_start + 1
        while i < len(line) and depth > 0:
            if line[i] == "(":
                depth += 1
            elif line[i] == ")":
                depth -= 1
            i += 1
        return line[paren_start+1:i-1]

    def translate_condition(self, cond):
        # Python to other languages
        if self.source_lang == "python":
            cond = cond.replace(" and ", " && ").replace(" or ", " || ").replace(" not ", " !")
            cond = cond.replace("True", "true").replace("False", "false")
            cond = cond.replace("None", "null")
        # Other languages to Python
        elif self.target_lang == "python":
            cond = cond.replace(" && ", " and ").replace(" || ", " or ").replace("!", " not ")
            cond = cond.replace("true", "True").replace("false", "False")
            cond = cond.replace("null", "None")
        return cond

    def translate_assignment(self, line):
        if "," in line.split("=")[0]:  # Multiple assignment
            lhs, rhs = line.split("=", 1)
            vars_list = [v.strip() for v in lhs.split(",")]
            vals_list = [v.strip() for v in rhs.split(",")]
            translated = []
            for v, val in zip(vars_list, vals_list):
                if self.target_lang in ["java", "c#", "c", "c++"]:
                    translated.append(f"Object {v} = {val};")
                elif self.target_lang == "javascript":
                    translated.append(f"let {v} = {val};")
                else:
                    translated.append(f"{v} = {val}")
            return "\n".join(translated)
        else:  # Single assignment
            parts = [p.strip() for p in line.split("=")]
            var = parts[0]
            value = "=".join(parts[1:])
            if self.target_lang in ["java", "c#", "c", "c++"]:
                return f"Object {var} = {value};"
            elif self.target_lang == "javascript":
                return f"let {var} = {value};"
            return line

    def translate_for_loop(self, line):
        # Python for loop
        match = re.match(r'for\s+(\w+)\s+in\s+range\((\d+)\s*,?\s*(\d+)?\s*\)\s*:', line)
        if match:
            var, start, end = match.groups()
            if not end:
                end = start
                start = "0"
            if self.target_lang in ["java", "c#", "c", "c++"]:
                return f"for (int {var} = {start}; {var} < {end}; {var}++) {{"
            if self.target_lang == "javascript":
                return f"for (let {var} = {start}; {var} < {end}; {var}++) {{"
        
        # for item in list
        match = re.match(r'for\s+(\w+)\s+in\s+(.+?)\s*:', line)
        if match:
            var, collection = match.groups()
            if self.target_lang in ["java", "c#"]:
                return f"for (Object {var} : {collection}) {{"
            if self.target_lang in ["c", "c++"]:
                return f"for (auto {var} : {collection}) {{"
            if self.target_lang == "javascript":
                return f"for (let {var} of {collection}) {{"
        
        return line

    def translate_append(self, line):
        match = re.match(r'(\w+)\.append\((.*?)\)', line)
        if match:
            var, item = match.groups()
            if self.target_lang in ["java", "c#"]:
                return f"{var}.add({item});"
            if self.target_lang == "javascript":
                return f"{var}.push({item});"
            if self.target_lang in ["c", "c++"]:
                return f"{var}.push_back({item});"
        return line

    def translate_list_operation(self, line):
        # Placeholder for more list operations
        return f"// {line}  # Translate list operation manually"

    def translate_dict(self, line):
        # Placeholder for dictionary translation
        return f"// {line}  # Dictionary translation"

    def translate_string_operation(self, line):
        # Placeholder for string operations
        return line

    def translate_lambda(self, line):
        # Placeholder for lambda translation
        return f"// {line}  # Lambda function"

    def translate_list_comprehension(self, line):
        # Placeholder for list comprehension
        return f"// {line}  # List comprehension"

    def translate_arrow_function(self, line):
        match = re.match(r'(const|let|var)\s+(\w+)\s*=\s*\((.*?)\)\s*=>\s*{?(.+)}?', line)
        if match and self.target_lang == "python":
            _, name, params, body = match.groups()
            return f"def {name}({params}):\n    return {body.strip()}"
        return line

    def translate_java_variable(self, line):
        if self.target_lang == "python":
            match = re.match(r'(int|float|double|String|boolean|char)\s+(\w+)\s*=\s*(.+);?', line)
            if match:
                _, var, value = match.groups()
                return f"{var} = {value}"
        return line

    def translate_c_variable(self, line):
        if self.target_lang == "python":
            match = re.match(r'(int|float|double|char)\s+(\w+)\s*=\s*(.+);?', line)
            if match:
                _, var, value = match.groups()
                return f"{var} = {value}"
        return line

    def translate_js_variable(self, line):
        if self.target_lang == "python":
            match = re.match(r'(let|const|var)\s+(\w+)\s*=\s*(.+);?', line)
            if match:
                _, var, value = match.groups()
                return f"{var} = {value}"
        return line

    def translate_js_array_method(self, line):
        if ".push(" in line and self.target_lang == "python":
            return line.replace(".push(", ".append(").rstrip(";")
        return line

    def from_java_control(self, line):
        if self.target_lang == "python":
            if line.startswith("if "):
                cond = re.search(r'if\s*\((.*?)\)', line)
                if cond:
                    return f"if {self.translate_condition(cond.group(1))}:"
            if "else if" in line:
                cond = re.search(r'else if\s*\((.*?)\)', line)
                if cond:
                    return f"elif {self.translate_condition(cond.group(1))}:"
            if line.startswith("else"):
                return "else:"
        return line

    def from_java_for_loop(self, line):
        if self.target_lang == "python":
            match = re.search(r'for\s*\((int\s+)?(\w+)\s*=\s*(\d+);\s*\2\s*<\s*(\d+);\s*\2\+\+\)', line)
            if match:
                var, start, end = match.group(2), match.group(3), match.group(4)
                return f"for {var} in range({start}, {end}):"
        return line


def translate_code(code, source_lang, target_lang):
    translator = CodeTranslator(source_lang, target_lang)
    lines = code.splitlines()
    translated_lines = []
    indent = 0
    
    for line in lines:
        if not line.strip():
            translated_lines.append("")
            continue
            
        t_line = translator.translate_line(line)
        
        # Handle indentation for brace-based languages
        if target_lang.lower() in ["java", "c#", "c", "c++", "javascript"]:
            if t_line.rstrip().endswith("{"):
                translated_lines.append("    " * indent + t_line)
                indent += 1
            elif t_line.strip() == "}" or t_line.strip().startswith("}"):
                indent -= 1
                translated_lines.append("    " * indent + t_line)
            else:
                translated_lines.append("    " * indent + t_line)
        else:
            # Python-style indentation
            translated_lines.append(t_line)
    
    return "\n".join(translated_lines)


@app.route("/", methods=["GET", "POST"])
def index():
    translated_code = ""
    if request.method == "POST":
        source_lang = request.form.get("source_lang")
        target_lang = request.form.get("target_lang")
        code = request.form.get("code")
        translated_code = translate_code(code, source_lang, target_lang)
    return render_template("index.html", translated_code=translated_code, languages=languages)


@app.route("/download", methods=["POST"])
def download():
    code = request.form.get("translated_code")
    buffer = io.StringIO()
    buffer.write(code)
    buffer.seek(0)
    return send_file(
        io.BytesIO(buffer.read().encode()),
        as_attachment=True,
        download_name="translated_code.txt",
        mimetype="text/plain"
    )


if __name__ == "__main__":
    app.run(debug=True)
