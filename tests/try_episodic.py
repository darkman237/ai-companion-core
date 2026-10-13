import tempfile

from companion.memory.episodic import EpisodicMemory

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    m = EpisodicMemory(d)
    m.add("User said they feel nervous about the cybersecurity exam", importance=0.8)
    m.add("User prefers vegetarian lunch")
    m.add("User went to the gym on Monday evening")

    for query in ["how does the user feel about exams?", "what does the user eat?"]:
        print(f"\nQ: {query}")
        for r in m.search(query, k=2):
            print(f"  {r['score']:.3f}  {r['text']}")