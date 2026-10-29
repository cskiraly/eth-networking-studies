// graphgen prints the harness's connection graph for a cell: gossipsim.RandomRegular(n, d, seed)
// (prysm testing/gossipsim/topology.go in snapshot fe605ca7e3, the same in every snapshot of this
// record), copied verbatim so the graph of any (nodes, degree, seed) can be regenerated without a
// cell. The harness builds a cell's graph with meshGraph -> randomRegular(n, SEGMENT_DEGREE,
// SEGMENT_SEED) and adds no edge after it.
//
//	go run ./scripts/bound/graphgen -n 500 -d 16 -seed 7 > edges.tsv
//
// Output: one line per edge, "a<TAB>b" with a < b, harness node indices (0 is the publisher).
package main

import (
	"bufio"
	"flag"
	"fmt"
	"math/rand/v2"
	"os"
	"slices"
)

const (
	swapsPerEdge         = 50
	regularGraphAttempts = 200
)

type Edge struct {
	A, B int
}

func NewEdge(i, j int) Edge {
	if i > j {
		i, j = j, i
	}
	return Edge{A: i, B: j}
}

func Circulant(n, d int) []Edge {
	present := make(map[Edge]bool, n*d/2)
	for i := range n {
		for k := 1; k <= d/2; k++ {
			present[NewEdge(i, (i+k)%n)] = true
		}
	}
	if d%2 == 1 {
		for i := range n / 2 {
			present[NewEdge(i, i+n/2)] = true
		}
	}
	return SortedEdges(present)
}

func RandomRegular(n, d int, seed uint64) ([]Edge, error) {
	if d >= n {
		return nil, fmt.Errorf("degree %d needs more than %d nodes", d, n)
	}
	if n*d%2 != 0 {
		return nil, fmt.Errorf("n*d must be even, got n=%d d=%d", n, d)
	}
	if d%2 == 1 && n%2 == 1 {
		return nil, fmt.Errorf("odd degree %d needs an even node count, got %d", d, n)
	}
	r := rand.New(rand.NewPCG(seed, seed^0x9e3779b97f4a7c15))
	es := Circulant(n, d)
	present := make(map[Edge]bool, len(es))
	for _, e := range es {
		present[e] = true
	}

	swap := func() {
		i, j := r.IntN(len(es)), r.IntN(len(es))
		if i == j {
			return
		}
		e1, e2 := es[i], es[j]
		var f1, f2 Edge
		if r.IntN(2) == 0 {
			f1, f2 = NewEdge(e1.A, e2.A), NewEdge(e1.B, e2.B)
		} else {
			f1, f2 = NewEdge(e1.A, e2.B), NewEdge(e1.B, e2.A)
		}
		if f1.A == f1.B || f2.A == f2.B || f1 == f2 || present[f1] || present[f2] {
			return
		}
		delete(present, e1)
		delete(present, e2)
		present[f1], present[f2] = true, true
		es[i], es[j] = f1, f2
	}

	for range swapsPerEdge * len(es) {
		swap()
	}
	// Swaps preserve degree but can in principle disconnect the graph, which would silently
	// starve some nodes of every message. Keep mixing rather than returning a split graph.
	for range regularGraphAttempts {
		if Connected(n, es) {
			return SortedEdges(present), nil
		}
		for range len(es) {
			swap()
		}
	}
	return nil, fmt.Errorf("no Connected %d-regular graph on %d nodes after mixing", d, n)
}

func SortedEdges(present map[Edge]bool) []Edge {
	out := make([]Edge, 0, len(present))
	for e := range present {
		out = append(out, e)
	}
	slices.SortFunc(out, func(x, y Edge) int {
		if x.A != y.A {
			return x.A - y.A
		}
		return x.B - y.B
	})
	return out
}

func Connected(n int, es []Edge) bool {
	if n == 0 {
		return true
	}
	adj := make([][]int, n)
	for _, e := range es {
		adj[e.A] = append(adj[e.A], e.B)
		adj[e.B] = append(adj[e.B], e.A)
	}
	seen := make([]bool, n)
	seen[0] = true
	queue := []int{0}
	count := 1
	for len(queue) > 0 {
		v := queue[0]
		queue = queue[1:]
		for _, w := range adj[v] {
			if !seen[w] {
				seen[w] = true
				count++
				queue = append(queue, w)
			}
		}
	}
	return count == n
}

func main() {
	n := flag.Int("n", 500, "nodes")
	d := flag.Int("d", 16, "connections per node (SEGMENT_DEGREE)")
	seed := flag.Uint64("seed", 7, "SEGMENT_SEED")
	flag.Parse()
	es, err := RandomRegular(*n, *d, *seed)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	w := bufio.NewWriter(os.Stdout)
	defer w.Flush()
	for _, e := range es {
		fmt.Fprintf(w, "%d\t%d\n", e.A, e.B)
	}
}
