package agentoscli

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

const Version = "0.1.0"

func Run(args []string, stdout io.Writer, stderr io.Writer) error {
	if len(args) == 0 {
		return runStartup(stdout, os.Stdin)
	}

	switch args[0] {
	case "--help", "-h", "help":
		printHelp(stdout)
	case "version":
		fmt.Fprintf(stdout, "AgentOS Personal %s\n", Version)
	case "doctor":
		return runDoctor(args[1:], stdout)
	case "init":
		return runInit(args[1:], stdout)
	case "install":
		fmt.Fprintln(stdout, installCommand())
	case "ui":
		return runStartup(stdout, os.Stdin)
	default:
		return fmt.Errorf("unknown command %q\n\nRun: agentos help", args[0])
	}
	return nil
}

func printHelp(w io.Writer) {
	fmt.Fprintln(w, `AgentOS Personal local-first agent operating system.

Usage:
  agentos <command> [options]

Commands:
  version   Show the AgentOS Personal version
  doctor    Diagnose the local Go CLI installation
  init      Create local AgentOS directories and default policy files
  ui        Show the AgentOS startup console
  install   Print the one-line installer command
  help      Show this help`)
}

func runStartup(stdout io.Writer, stdin io.Reader) error {
	root, err := filepath.Abs(".")
	if err != nil {
		return err
	}
	fmt.Fprint(stdout, startupView(root))
	return runPrompt(stdout, stdin)
}

func startupView(root string) string {
	agentosDir := filepath.Join(root, ".agentos")
	policiesDir := filepath.Join(root, "policies")
	return fmt.Sprintf(`╭────────────────────────────────────────────────────────────╮
│ AGENTOS PERSONAL                                           │
│ Local-first agent workspace                                │
╰────────────────────────────────────────────────────────────╯

Workspace
  root          %s
  runtime       Go CLI %s
  profile       default

Gentle AI Complements
  memory        local SQLite technical memory
  sdd           OpenSpec workflow and change artifacts
  skills        local skill registry
  policies      safety checks for paths and commands
  streaming     chat stream events and usage accounting

Status
  agentos dir   %s
  policies      %s

Commands
  agentos init                 create local workspace files
  agentos doctor               inspect local setup
  agentos version              show version
  agentos help                 list commands
  exit                         close this console

agentos › `,
		root,
		Version,
		statusLabel(dirExists(agentosDir)),
		statusLabel(dirExists(policiesDir)),
	)
}

func runPrompt(stdout io.Writer, stdin io.Reader) error {
	scanner := bufio.NewScanner(stdin)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		switch line {
		case "", "exit", "quit":
			fmt.Fprintln(stdout, "Goodbye.")
			return nil
		case "help":
			printHelp(stdout)
		case "version":
			fmt.Fprintf(stdout, "AgentOS Personal %s\n", Version)
		case "doctor":
			if err := runDoctor(nil, stdout); err != nil {
				return err
			}
		case "init":
			if err := runInit(nil, stdout); err != nil {
				return err
			}
		default:
			fmt.Fprintf(stdout, "Unknown console command %q. Try: help, doctor, init, version, exit.\n", line)
		}
		fmt.Fprint(stdout, "agentos › ")
	}
	if err := scanner.Err(); err != nil {
		return err
	}
	return nil
}

func statusLabel(ok bool) string {
	if ok {
		return "ready"
	}
	return "missing"
}

func runDoctor(args []string, stdout io.Writer) error {
	root, err := rootFromArgs(args)
	if err != nil {
		return err
	}
	root, err = filepath.Abs(root)
	if err != nil {
		return err
	}

	fmt.Fprintln(stdout, "AgentOS Doctor")
	check(stdout, "go-runtime", true, runtime.Version())
	check(stdout, "platform", true, runtime.GOOS+"/"+runtime.GOARCH)
	check(stdout, "project-root", fileExists(filepath.Join(root, "pyproject.toml")) || fileExists(filepath.Join(root, "go.mod")), root)
	check(stdout, "agentos-dir", dirExists(filepath.Join(root, ".agentos")), filepath.Join(root, ".agentos"))
	check(stdout, "policies", fileExists(filepath.Join(root, "policies", "sensitive_paths.yaml")) && fileExists(filepath.Join(root, "policies", "destructive_commands.yaml")), filepath.Join(root, "policies"))
	return nil
}

func runInit(args []string, stdout io.Writer) error {
	root, err := rootFromArgs(args)
	if err != nil {
		return err
	}
	root, err = filepath.Abs(root)
	if err != nil {
		return err
	}

	paths := []string{
		filepath.Join(root, ".agentos", "agents"),
		filepath.Join(root, ".agentos", "brain"),
		filepath.Join(root, "skills"),
		filepath.Join(root, "openspec", "specs"),
		filepath.Join(root, "openspec", "changes"),
		filepath.Join(root, "policies"),
	}
	for _, path := range paths {
		if err := os.MkdirAll(path, 0o755); err != nil {
			return err
		}
	}

	files := map[string]string{
		filepath.Join(root, "policies", "sensitive_paths.yaml"):      "sensitive_paths:\n  - .env\n  - .env.*\n  - secrets/\n  - credentials/\n  - .ssh/\n",
		filepath.Join(root, "policies", "destructive_commands.yaml"): "destructive_commands:\n  - rm -rf\n  - git push --force\n  - drop database\n  - chmod -R\n  - chown -R\n",
		filepath.Join(root, "policies", "approval_rules.yaml"):       "approval_commands:\n  - git push\n  - backup restore\n  - agentos usage reset\n",
	}
	for path, content := range files {
		if err := writeIfMissing(path, content); err != nil {
			return err
		}
	}

	fmt.Fprintf(stdout, "Initialized AgentOS project at %s\n", root)
	return nil
}

func rootFromArgs(args []string) (string, error) {
	root := "."
	for index := 0; index < len(args); index++ {
		arg := args[index]
		switch {
		case arg == "--root":
			if index+1 >= len(args) {
				return "", errors.New("--root requires a path")
			}
			root = args[index+1]
			index++
		case strings.HasPrefix(arg, "--root="):
			root = strings.TrimPrefix(arg, "--root=")
		default:
			return "", fmt.Errorf("unknown option %q", arg)
		}
	}
	return root, nil
}

func check(w io.Writer, name string, ok bool, detail string) {
	status := "pass"
	if !ok {
		status = "warn"
	}
	fmt.Fprintf(w, "%-12s %-4s %s\n", name, status, detail)
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func dirExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

func writeIfMissing(path string, content string) error {
	if fileExists(path) {
		return nil
	}
	return os.WriteFile(path, []byte(content), 0o644)
}

func installCommand() string {
	return "curl -fsSL https://raw.githubusercontent.com/AlejandroPalmieri/My-ai/main/scripts/install.sh | sh"
}
