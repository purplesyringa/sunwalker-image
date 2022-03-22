#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
import itertools
import json
import sys
import tarfile


class GenerationError(Exception):
    pass


class MakefileParser:
    def __init__(self, code: str):
        self.code: str = code
        self.non_exact_target_names: bool = False
        self.artifacts: set[str] = set()
        self.inputs: set[str] = set()
        self.identify_lisp: Optional[str] = None
        self.base_rule_lisp: str = "(var \"$base\")"
        self.build_statements: list[Statement] = []
        self.run_lisp: Optional[str] = None


    def parse(self) -> str:
        # Split into rules
        current_rule = ""
        current_rule_code = ""
        for line in self.code.splitlines():
            if line.startswith("\t"):
                if current_rule == "":
                    raise GenerationError("The first line of each rule must not start with a tab")
                current_rule_code += line[1:] + "\n"
            else:
                if current_rule != "":
                    self.parse_rule(current_rule, current_rule_code)
                current_rule = line
                current_rule_code = ""
        if current_rule != "":
            self.parse_rule(current_rule, current_rule_code)

        if not self.build_statements:
            build_lisp = "nil"
        elif len(self.build_statements) == 1:
            build_lisp = self.build_statements[0].to_lisp()
        else:
            build_lisp = f"(seq {' '.join(statement.to_lisp() for statement in self.build_statements)})"

        if self.identify_lisp is None:
            raise GenerationError("'identify' target is missing")
        if self.run_lisp is None:
            raise GenerationError("'run' target is missing")
        if not self.inputs:
            raise GenerationError("No inputs detected")

        inputs = f"(list {' '.join(json.dumps(input) for input in self.inputs)})"
        lisp = f"(language {self.identify_lisp} {self.base_rule_lisp} {inputs} {build_lisp} {self.run_lisp})"
        return lisp


    def parse_rule(self, rule: str, code: str):
        targets, prerequisites = self.parse_rule_header(rule)
        if targets == [".NON_EXACT_TARGET_NAMES"]:
            self.non_exact_target_names = True
            return

        # Ensure that all prerequisites come from somewhere
        for prerequisite in prerequisites:
            if prerequisite not in self.artifacts:
                self.inputs.add(prerequisite)

        # Parse body
        statements = self.parse_rule_code(code)

        # Substitute metavars
        def factory(s):
            if "%" in s:
                if self.non_exact_target_names:
                    return GlobToken(s)
                else:
                    tokens = []
                    for i, chunk in enumerate(s.split("%")):
                        if i > 0:
                            tokens.append(MetaVariableToken("$base"))
                        if chunk:
                            tokens.append(StringToken(chunk))
                    if len(tokens) == 1:
                        return tokens[0]
                    else:
                        return ConcatToken(tokens)
            else:
                return StringToken(s)
        vars = {}
        if prerequisites:
            vars["$<"] = factory(prerequisites[0])
        if targets:
            vars["$@"] = factory(targets[0])
        statements = [statement.substitute_variables(vars) for statement in statements]

        if targets == ["run"]:
            if len(statements) != 1 or not isinstance(statements[0], ExecStatement):
                # This is because we don't spawn a full process tree as real shells do, not really. Instead, we execute
                # commands synchronously and pass around strings. This is fine for compilation, but not for judging.
                raise GenerationError("'run' target must contain a single statement")

            argv = statements[0].tokens
            prerequisites_code = f"(list {' '.join(factory(prerequisite).to_lisp() for prerequisite in prerequisites)})"
            argv_code = f"(list {' '.join(arg.to_lisp() for arg in argv)})"
            self.run_lisp = f"(run {prerequisites_code} {argv_code})"
        elif targets == ["identify"]:
            if prerequisites:
                raise GenerationError("'identify' target must not have prerequisites")
            if len(statements) == 1:
                insn = statements[0].to_lisp()
            else:
                insn = f"(seq {' '.join(statement.to_lisp() for statement in statements)})"
            self.identify_lisp = insn
        elif targets == ["base_rule"]:
            if len(statements) == 1:
                insn = statements[0].to_lisp()
            else:
                insn = f"(seq {' '.join(statement.to_lisp() for statement in statements)})"
            self.base_rule_lisp = insn
        else:
            # Resolve targets
            if targets:
                keyword = "glob" if self.non_exact_target_names else "subst"
                targets_code = f"(list {' '.join('(' + keyword + ' ' + json.dumps(prerequisite) + ')' for prerequisite in targets)})"
            else:
                targets_code = "nil"

            # Generate targets as artifacts
            for target in targets:
                if target in self.artifacts:
                    raise GenerationError(f"Rule {rule} overrides existing artifact {target}")
                self.artifacts.add(target)

            self.build_statements += statements


    def parse_rule_header(self, rule: str) -> tuple[list[str], list[str]]:
        targets, _, prerequisites = rule.partition(":")
        return targets.split(), prerequisites.split()


    def parse_rule_code(self, code: str) -> list[Statement]:
        statements = []
        for line in code.splitlines():
            statements.append(StatementParser(line).parse_statement())
        return statements


class Statement:
    def to_lisp(self, input=None) -> str:
        raise NotImplementedError()
    def substitute_variables(self, vars: dict[str, str]):
        raise NotImplementedError()

@dataclass
class ExecStatement(Statement):
    tokens: list[Token]
    def __str__(self):
        return " ".join(map(str, self.tokens))
    def to_lisp(self, input=None):
        if self.tokens:
            argv = f"(list {' '.join(token.to_lisp() for token in self.tokens)})"
        else:
            argv = "nil"
        if input is None:
            return f"(exec {argv})"
        else:
            return f"(exec_with {input} {argv}"
    def substitute_variables(self, vars: dict[str, str]):
        return ExecStatement([token.substitute_variables(vars) for token in self.tokens])

@dataclass
class PipeStatement(Statement):
    stmts: list[Statement]
    def __str__(self):
        return " | ".join(map(str, self.stmts))
    def to_lisp(self, input=None):
        if len(self.stmts) == 1:
            return self.stmts[0].to_lisp(input=input)
        return self.stmts[-1].to_lisp(input=PipeStatement(self.stmts[:-1]).to_lisp(input))
    def substitute_variables(self, vars: dict[str, str]):
        return PipeStatement([stmt.substitute_variables(vars) for stmt in self.stmts])

class Token:
    def to_lisp(self) -> str:
        raise NotImplementedError()
    def substitute_variables(self, vars: dict[str, str]):
        raise NotImplementedError()

@dataclass
class ConcatToken(Token):
    tokens: list[Token]
    def __str__(self):
        return "".join(map(str, self.tokens))
    def to_lisp(self):
        return f"(concat {' '.join(atom.to_lisp() for atom in self.tokens)})"
    def substitute_variables(self, vars: dict[str, str]):
        return ConcatToken([token.substitute_variables(vars) for token in self.tokens])

@dataclass
class StringToken(Token):
    s: str
    def __str__(self):
        if all(c.isalnum() or c in "-+@=/" for c in self.s):
            return self.s
        else:
            return json.dumps(self.s)
    def to_lisp(self):
        return json.dumps(self.s)
    def substitute_variables(self, vars: dict[str, str]):
        return self

@dataclass
class SubShellToken(Token):
    stmt: Statement
    def __str__(self):
        return f"\"$({self.stmt})\""
    def to_lisp(self):
        return self.stmt.to_lisp()
    def substitute_variables(self, vars: dict[str, str]):
        return SubShellToken(self.stmt.substitute_variables(vars))

@dataclass
class MetaVariableToken(Token):
    name: str
    def __str__(self):
        return self.name
    def to_lisp(self):
        return f"(var {json.dumps(self.name)})"
    def substitute_variables(self, vars: dict[str, str]):
        return vars[self.name]

@dataclass
class GlobToken(Token):
    pattern: str
    def __str__(self):
        return self.pattern.sub("%", "*")
    def to_lisp(self, input=None):
        return f"(glob {json.dumps(self.pattern)})"
    def substitute_variables(self, vars: dict[str, str]):
        return self

def helper_to_string(token):
    if isinstance(token, StringToken):
        return token.s
    else:
        raise GenerationError(f"Expected a single string literal, found {token}")

class BuiltinCommand(Statement):
    def __init__(self, argv: list[Token]):
        raise NotImplementedError()

class EchoBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        self.argv = argv
    def __str__(self):
        return "echo " + " ".join(map(str, self.argv))
    def to_lisp(self, input=None) -> str:
        if input is not None:
            raise GenerationError("echo does not expect input")
        if len(self.argv) == 1:
            return self.argv[0].to_lisp()
        else:
            to_concat: list[str] = []
            for arg in self.argv:
                if to_concat:
                    to_concat.append(StringToken(" "))
                else:
                    to_concat.append(arg)
            return ConcatToken(to_concat).to_lisp()
    def substitute_variables(self, vars: dict[str, str]):
        return EchoBuiltinCommand([arg.substitute_variables(vars) for arg in self.argv])

class HeadBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        if len(argv) != 1:
            raise GenerationError("head takes a single argument of kind '-<num>'")
        num = helper_to_string(argv[0])
        if num[0] != "-":
            raise GenerationError("head takes a single argument of kind '-<num>'")
        self.n_lines = int(num[1:])
    def __str__(self):
        return f"head -{self.n_lines}"
    def to_lisp(self, input=None) -> str:
        if input is None:
            raise GenerationError("head expects input")
        return f"(head {self.n_lines} {input})"
    def substitute_variables(self, vars: dict[str, str]):
        return self

class TailBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        if len(argv) != 1:
            raise GenerationError("tail takes a single argument of kind '-<num>'")
        num = helper_to_string(argv[0])
        if num[0] != "-":
            raise GenerationError("tail takes a single argument of kind '-<num>'")
        self.n_lines = int(num[1:])
    def __str__(self):
        return f"tail -{self.n_lines}"
    def to_lisp(self, input=None) -> str:
        if input is None:
            raise GenerationError("tail expects input")
        return f"(tail {self.n_lines} {input})"
    def substitute_variables(self, vars: dict[str, str]):
        return self

class SedBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        if len(argv) != 1:
            raise GenerationError("sed takes a single argument")
        pattern = helper_to_string(argv[0])

        if pattern[0] != "s" or pattern[1] != pattern[-1]:
            raise GenerationError(f"sed pattern must be of kind s/.../.../ (or with different delimiters), found: {pattern}")
        re, _, repl = pattern[2:-1].partition(pattern[1])
        self.re = re
        self.repl = repl
    def __str__(self):
        return f"sed s/{self.re}/{self.repl}/"
    def to_lisp(self, input=None) -> str:
        if input is None:
            raise GenerationError("sed expects input")
        return f"(sed {json.dumps(self.re)} {json.dumps(self.repl)} {input})"
    def substitute_variables(self, vars: dict[str, str]):
        return self

class CutBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        argv = [helper_to_string(arg) for arg in argv]
        self.delimiter = "\t"
        self.fields = []
        for arg in argv:
            if arg.startswith("-d"):
                self.delimiter = arg[2:]
            elif arg.startswith("-f"):
                fields = arg[2:]
                for field_range in fields.split(","):
                    if field_range.endswith("-"):
                        self.fields.append((int(field_range[:-1]) - 1, None))
                    elif field_range.startswith("-"):
                        self.fields.append((0, int(field_range[1:])))
                    elif "-" in field_range:
                        from_, to = field_range.split("-")
                        self.fields.append((int(from_) - 1, int(to)))
                    else:
                        field = int(field_range) - 1
                        self.fields.append((field, field + 1))
            else:
                raise GenerationError(f"Unknown option {arg} to cut")
    def __str__(self):
        fields = ",".join(
            str(rng[0] + 1)
            if rng[0] + 1 == rng[1]
            else str(rng[0] + 1) + "-" + ("" if rng[1] is None else str(rng[1]))
            for rng in self.fields
        )
        return f"cut -d{repr(self.delimiter)} -f{fields}"
    def to_lisp(self, input=None) -> str:
        if input is None:
            raise GenerationError("cut expects input")
        def format_range(l, r):
            if l + 1 == r:
                return str(l)
            else:
                return f"(range {l} {'nil' if r is None else r})"
        if len(self.fields) == 1:
            fields = format_range(*self.fields[0])
        else:
            fields = f"(concat {' '.join(format_range(*rng) for rng in self.fields)})"
        return f"(cut {input} {json.dumps(self.delimiter)} {fields})"
    def substitute_variables(self, vars: dict[str, str]):
        return self

class GrepBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        argv = [helper_to_string(arg) for arg in argv]
        self.stop_after_n_matches = None
        if argv[0].startswith("-m"):
            self.stop_after_n_matches = int(argv[0][2:])
            argv.pop(0)
        if len(argv) != 1:
            raise GenerationError(f"grep takes a pattern, optionally lead by -m<num>")
        self.pattern = argv[0]
    def __str__(self):
        return "grep" + (f" -m{self.stop_after_n_matches}" if self.stop_after_n_matches is not None else "") + f" {self.pattern}"
    def to_lisp(self, input=None) -> str:
        if input is None:
            raise GenerationError("grep expects input")
        return f"(grep {json.dumps(self.pattern)} {input})"
    def substitute_variables(self, vars: dict[str, str]):
        return self

class BasenameBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        if len(argv) != 1:
            raise GenerationError("basename takes a single argument")
        self.path = argv[0]
    def __str__(self):
        return f"basename {self.path}"
    def to_lisp(self, input=None) -> str:
        if input is not None:
            raise GenerationError("basename does not expect input")
        return f"(basename {self.path.to_lisp()})"
    def substitute_variables(self, vars: dict[str, str]):
        return BasenameBuiltinCommand([self.path.substitute_variables(vars)])

class CatBuiltinCommand(BuiltinCommand):
    def __init__(self, argv):
        if len(argv) != 1:
            raise GenerationError("cat takes a single arugment")
        self.file = argv[0]
    def __str__(self):
        return f"cat {self.file}"
    def to_lisp(self, input=None) -> str:
        if input is not None:
            raise GenerationError("cat does not expect input")
        return f"(cat {self.file.to_lisp()})"
    def substitute_variables(self, vars: dict[str, str]):
        return CatBuiltinCommand([self.file.substitute_variables(vars)])

BUILTIN_COMMANDS: dict[str, Type[BuiltinCommand]] = {
    "echo": EchoBuiltinCommand,
    "head": HeadBuiltinCommand,
    "tail": TailBuiltinCommand,
    "sed": SedBuiltinCommand,
    "cut": CutBuiltinCommand,
    "grep": GrepBuiltinCommand,
    "basename": BasenameBuiltinCommand,
    "cat": CatBuiltinCommand
}


class StatementParser:
    def __init__(self, code: str):
        self.code: str = code
        self.pos: int = 0


    def parse_statement(self, terminate_on=None) -> Statement:
        tokens: list[Token] = []
        piped_statements: list[Statement] = []
        while True:
            self.skip_whitespace()
            if self.try_consume(terminate_on):
                break
            if self.try_consume("|"):
                piped_statements.append(self.tokens_to_statement(tokens))
                tokens = []
                continue
            tokens.append(self.parse_token(terminate_on=terminate_on))
        piped_statements.append(self.tokens_to_statement(tokens))
        if len(piped_statements) == 1:
            return piped_statements[0]
        else:
            return PipeStatement(piped_statements)


    def parse_token(self, terminate_on=None) -> Token:
        atoms = []

        while not self.matches(terminate_on) and not self.code[self.pos].isspace():
            if self.try_consume("\""):
                while not self.try_consume("\""):
                    atoms.append(self.parse_atom())
            else:
                atom = self.parse_atom()
                if not isinstance(atom, StringToken):
                    raise GenerationError(f"Complex atoms MUST be wrapped in quotes: {atom}")
                atoms.append(atom)

        # Group string atoms
        new_atoms: list[Atom] = []
        for is_string_atoms, atoms in itertools.groupby(atoms, key=lambda atom: isinstance(atom, StringToken)):
            if is_string_atoms:
                new_atoms.append(StringToken("".join(atom.s for atom in atoms)))
            else:
                new_atoms += atoms

        if len(new_atoms) == 1:
            return new_atoms[0]
        else:
            return ConcatToken(new_atoms)


    def parse_atom(self) -> Atom:
        if self.code[self.pos] == "\"":
            raise GenerationError("Unescaped quotation mark in the middle of token")

        if self.try_consume("$("):
            return SubShellToken(self.parse_statement(terminate_on=")"))

        if self.try_consume("$<"):
            return MetaVariableToken("$<")
        elif self.try_consume("$^"):
            # TODO: is this useful to be supported? The problem is that $^ requires variable splitting, which we don't
            # support.
            raise GenerationError("Use $< instead of $^")
        elif self.try_consume("$@"):
            return MetaVariableToken("$@")

        atom = self.code[self.pos]
        self.pos += 1
        return StringToken(atom)


    def skip_whitespace(self):
        while self.pos < len(self.code) and self.code[self.pos].isspace():
            self.pos += 1


    def matches(self, ch):
        if ch is None:
            return self.pos == len(self.code)
        return self.code[self.pos:self.pos + len(ch)] == ch


    def try_consume(self, ch):
        if self.matches(ch):
            if ch is not None:
                self.pos += len(ch)
            return True
        else:
            return False


    def tokens_to_statement(self, tokens: list[Token]):
        if isinstance(tokens[0], StringToken) and tokens[0].s in BUILTIN_COMMANDS:
            return BUILTIN_COMMANDS[tokens[0].s](tokens[1:])
        else:
            return ExecStatement(tokens)


class PackageConfigGenerator:
    def __init__(self, name: str, path: str):
        self.name: str = name  # name of package
        self.path: str = path  # path to package directory


    def generate_config(self) -> str:
        print("Generating config for", self.name)

        """
        tar_path = os.path.join(self.path, self.name + ".tar.gz")
        environment: dict[str, str] = {}
        with tarfile.open(tar_path) as f_tar:
            with f_tar.extractfile(".sunwalker/env") as f_env:
                for line in f_env.read().decode().splitlines():
                    name, value = line.partition("=")
                    environment[name] = value
        """

        languages = []

        for language in os.listdir(os.path.join(self.path, "languages")):
            assert language.endswith(".make")
            language = language[:-5]

            with open(os.path.join(self.path, "languages", language + ".make")) as f:
                makefile = f.read()

            try:
                language_config = MakefileParser(makefile).parse()
            except GenerationError as e:
                raise GenerationError(f"Error while parsing makefile at {self.name}/languages/{language}.make")

            languages.append(f"(pair {json.dumps(language)} {language_config})")

        languages_code = f"(map (list {' '.join(languages)}))" if languages else "nil"

        return f"(package {languages_code})"



def main():
    if len(sys.argv) == 1:
        package_names = os.listdir("packages")
    else:
        package_names = sys.argv[1:]

    packages = []
    for package_name in package_names:
        path = os.path.join("packages", package_name)
        code = PackageConfigGenerator(package_name, path).generate_config()
        packages.append(f"(pair {json.dumps(package_name)} {code})")

    packages_code = f"(map (list {' '.join(packages)}))" if packages else "nil"
    config = f"(config {packages_code})"

    with open("image.cfg", "w") as f:
        f.write(config)


if __name__ == "__main__":
    main()
