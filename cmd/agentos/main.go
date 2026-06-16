package main

import (
	"fmt"
	"os"

	"github.com/AlejandroPalmieri/My-ai/internal/agentoscli"
)

func main() {
	if err := agentoscli.Run(os.Args[1:], os.Stdout, os.Stderr); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
