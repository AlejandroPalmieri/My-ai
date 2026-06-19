package agentoscli

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunWithoutArgsShowsStartupConsole(t *testing.T) {
	var stdout bytes.Buffer

	err := Run(nil, &stdout, &bytes.Buffer{})

	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}
	for _, want := range []string{"AGENTOS PERSONAL", "Gentle AI Complements", "agentos ›"} {
		if !strings.Contains(stdout.String(), want) {
			t.Fatalf("startup output missing %q: %q", want, stdout.String())
		}
	}
}

func TestRunVersion(t *testing.T) {
	var stdout bytes.Buffer

	err := Run([]string{"version"}, &stdout, &bytes.Buffer{})

	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}
	if got := stdout.String(); !strings.Contains(got, "AgentOS Personal 0.3.0") {
		t.Fatalf("version output = %q", got)
	}
}

func TestRunInitCreatesLocalProjectScaffold(t *testing.T) {
	root := t.TempDir()
	var stdout bytes.Buffer

	err := Run([]string{"init", "--root", root}, &stdout, &bytes.Buffer{})

	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}
	for _, path := range []string{
		filepath.Join(root, ".agentos", "agents"),
		filepath.Join(root, ".agentos", "brain"),
		filepath.Join(root, "openspec", "changes"),
		filepath.Join(root, "policies", "sensitive_paths.yaml"),
		filepath.Join(root, "policies", "destructive_commands.yaml"),
		filepath.Join(root, "policies", "approval_rules.yaml"),
	} {
		if _, err := os.Stat(path); err != nil {
			t.Fatalf("expected %s to exist: %v", path, err)
		}
	}
	if got := stdout.String(); !strings.Contains(got, "Initialized AgentOS project") {
		t.Fatalf("init output = %q", got)
	}
}

func TestRunDoctorReportsEnvironment(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module demo\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := Run([]string{"init", "--root", root}, &bytes.Buffer{}, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	var stdout bytes.Buffer

	err := Run([]string{"doctor", "--root", root}, &stdout, &bytes.Buffer{})

	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}
	for _, want := range []string{"AgentOS Doctor", "go-runtime", "project-root", "policies"} {
		if !strings.Contains(stdout.String(), want) {
			t.Fatalf("doctor output missing %q: %q", want, stdout.String())
		}
	}
}

func TestRunRejectsUnknownCommand(t *testing.T) {
	err := Run([]string{"missing"}, &bytes.Buffer{}, &bytes.Buffer{})

	if err == nil || !strings.Contains(err.Error(), "unknown command") {
		t.Fatalf("expected unknown command error, got %v", err)
	}
}
