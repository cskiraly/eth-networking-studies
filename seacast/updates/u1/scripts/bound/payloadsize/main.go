// payloadsize prints each message's compressed size and SEACAST's chunking as the harness builds
// them (beacon-chain/p2p/segmentintegrationtest/q6cell_test.go, c.build, in prysm snapshot
// fe605ca7e3): message 1 from seed 11, message m > 1 from seed 1000+m;
// MainnetLikePayload, snappy block encoding (SEGMENT_COMPRESS_FIRST), K = SEGMENT_FIXED_COUNT data
// chunks of ceil(len/K), the last one shorter. Also the whole message as gossipsub and the RS arm
// send it (wholeArm: the payload as an SSZ byte list, a 4-byte offset first, snappy-encoded by
// SszNetworkEncoder.EncodeGossip), and the RS arm's data chunks of 16384 B, padded.
//
//	go run . -n 1048576 -k 64 -msgs 6 > ../../../data/payload-sizes.tsv
package main

import (
	"flag"
	"fmt"

	"github.com/golang/snappy"
)

const rsChunk = 16384 // the RS arm's ChunkLen (ecrs_test.go in prysm snapshot fe605ca7e3)

func main() {
	n := flag.Int("n", 1<<20, "payload bytes (SEGMENT_PAYLOAD_BYTES)")
	k := flag.Int("k", 64, "data chunks (SEGMENT_FIXED_COUNT)")
	msgs := flag.Int("msgs", 6, "messages per cell")
	flag.Parse()
	fmt.Println("msg\tseed\tcompressed_bytes\tchunk_bytes\tlast_chunk_bytes\twhole_bytes\trs_chunks\trs_bytes")
	for m := 1; m <= *msgs; m++ {
		seed := uint64(11)
		if m > 1 {
			seed = uint64(1000 + m)
		}
		payload := MainnetLikePayload(*n, seed)
		wire := snappy.Encode(nil, payload)
		unit := (len(wire) + *k - 1) / *k
		ssz := append([]byte{4, 0, 0, 0}, payload...)
		whole := len(snappy.Encode(nil, ssz))
		rs := (whole + rsChunk - 1) / rsChunk
		fmt.Printf("%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n", m, seed, len(wire), unit, len(wire)-(*k-1)*unit, whole, rs, rs*rsChunk)
	}
}
