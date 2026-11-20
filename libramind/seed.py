"""
seed.py – Populate the LibraMind database with extensive books, students,
loans, reservations, and rebuild the vector search indexes.
"""
import sqlite3
import os
from datetime import date, timedelta
from db import get_conn, init_db
from config import DB_PATH

TODAY = date.today()


def td(days: int) -> str:
    """Return ISO date string offset from today by `days`."""
    return (TODAY + timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# 1. Reset Database
# ---------------------------------------------------------------------------
if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
    except Exception:
        pass
init_db()

conn = get_conn()
cur = conn.cursor()

# ---------------------------------------------------------------------------
# 2. Books Catalog (85+ realistic books with rich summaries)
#    Tuple format: (title, author, subject, isbn, description, year, language, total_copies, available_copies)
# ---------------------------------------------------------------------------
books = [
    # --- DSA ---
    ("Introduction to Algorithms", "Cormen, Leiserson, Rivest, Stein", "DSA",
     "9780262033848", "The definitive algorithms textbook, widely known as CLRS. Covers asymptotic analysis, sorting algorithms, dynamic programming, greedy algorithms, and advanced graph techniques with rigorous mathematical proofs.", 2009, "English", 4, 3),
    ("Data Structures and Algorithm Analysis in C++", "Mark Allen Weiss", "DSA",
     "9780132847377", "Detailed exploration of classical data structures such as balanced binary search trees, heaps, and hash tables. Features concrete C++ implementations emphasizing object-oriented efficiency and time complexity.", 2013, "English", 3, 2),
    ("Algorithms", "Robert Sedgewick, Kevin Wayne", "DSA",
     "9780321573513", "Comprehensive guide to essential algorithms and data structures implemented in Java. Includes extensive real-world applications, performance benchmarks, and clear visual diagrams.", 2011, "English", 3, 3),
    ("The Algorithm Design Manual", "Steven S. Skiena", "DSA",
     "9781849967204", "A practical handbook for real-world algorithm design. Divided into design techniques and a comprehensive algorithmic catalog with insightful 'war stories' from engineering practice.", 2008, "English", 2, 1),
    ("Cracking the Coding Interview", "Gayle Laakmann McDowell", "DSA",
     "9780984782857", "189 detailed programming questions and systematic solutions covering arrays, strings, trees, bit manipulation, and system design for technical software interviews.", 2015, "English", 5, 4),
    ("Grokking Algorithms", "Aditya Bhargava", "DSA",
     "9781617292231", "A friendly, fully illustrated guide to algorithms for visual learners. Explains search, recursion, hash tables, breadth-first search, and Dijkstra's algorithm using intuitive hand-drawn diagrams.", 2016, "English", 4, 3),

    # --- OS ---
    ("Operating System Concepts", "Silberschatz, Galvin, Gagne", "OS",
     "9781118063330", "The famous Dinosaur book. Provides fundamental grounding in process synchronization, thread concurrency, memory management, virtual memory, paging, and distributed file systems.", 2018, "English", 4, 3),
    ("Modern Operating Systems", "Andrew S. Tanenbaum", "OS",
     "9780133591620", "In-depth classic on operating system principles, IPC, deadlocks, virtualization, multi-core architecture, and security by a legendary computer scientist.", 2014, "English", 3, 2),
    ("Operating Systems: Three Easy Pieces", "Remzi Arpaci-Dusseau, Andrea Arpaci-Dusseau", "OS",
     "9781985086593", "Acclaimed conceptual textbook structured around three pillars: virtualization of CPU and memory, concurrency bugs and locks, and persistence with file systems and crash recovery.", 2018, "English", 2, 2),
    ("Linux Kernel Development", "Robert Love", "OS",
     "9780672329463", "Practical insights into the design and implementation of the Linux kernel, process scheduling, memory addressing, interrupts, and device drivers.", 2010, "English", 2, 1),

    # --- DBMS ---
    ("Database System Concepts", "Silberschatz, Korth, Sudarshan", "DBMS",
     "9780078022159", "Foundational text covering relational models, SQL dialectics, indexing using B+ trees, query optimization, ACID transactions, and distributed databases.", 2019, "English", 4, 3),
    ("Fundamentals of Database Systems", "Elmasri, Navathe", "DBMS",
     "9780133970777", "Clear introduction to relational schema design, ER modeling, normalization rules (1NF to BCNF), and NoSQL architectures with practical database application examples.", 2015, "English", 3, 2),
    ("Database Management Systems", "Ramakrishnan, Gehrke", "DBMS",
     "9780072465631", "The 'Cow Book' offering comprehensive, implementation-focused coverage of storage engines, buffer pool management, concurrency control, and query evaluation.", 2002, "English", 2, 2),
    ("Designing Data-Intensive Applications", "Martin Kleppmann", "DBMS",
     "9781449373320", "Modern masterpiece on distributed data systems, replication algorithms, partitioning, consensus protocols, batch processing, and event streams. Crucial for system architecture.", 2017, "English", 3, 0),

    # --- Networks ---
    ("Computer Networks", "Andrew S. Tanenbaum, David Wetherall", "Networks",
     "9780132126953", "Comprehensive breakdown of networking architecture covering physical media, wireless protocols, network routing, TCP/UDP transport, and modern internet application layers.", 2010, "English", 3, 3),
    ("Computer Networking: A Top-Down Approach", "Kurose, Ross", "Networks",
     "9780133594140", "Pedagogical classic exploring networking from the user-facing application layer down to the physical wire, enriched with Wireshark packet capture labs and socket programming.", 2016, "English", 4, 3),
    ("Data Communications and Networking", "Behrouz A. Forouzan", "Networks",
     "9780073376226", "Approachable and visually illustrated text on signals, multiplexing, error detection and correction, IP subnetting, and network security protocols.", 2012, "English", 2, 1),
    ("TCP/IP Illustrated, Volume 1", "W. Richard Stevens", "Networks",
     "9780321336316", "The premier guide to the TCP/IP protocol suite detailing actual packet exchanges, flow control, window management, and congestion algorithms.", 2011, "English", 2, 1),

    # --- AI & Machine Learning ---
    ("Artificial Intelligence: A Modern Approach", "Stuart Russell, Peter Norvig", "AI",
     "9780136042594", "The authoritative AI curriculum reference. Covers rational agent architectures, search algorithms, knowledge representation, probabilistic reasoning, and machine perception.", 2020, "English", 4, 3),
    ("Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow", "Aurélien Géron", "ML",
     "9781492032649", "The ultimate hands-on ML guide with end-to-end projects covering regression, classification, random forests, neural nets, embeddings, and generative models.", 2019, "English", 5, 4),
    ("Pattern Recognition and Machine Learning", "Christopher Bishop", "ML",
     "9780387310732", "Advanced mathematical treatment of machine learning using Bayesian probabilities, graphical models, expectation maximization, and kernel methods.", 2006, "English", 3, 2),
    ("The Hundred-Page Machine Learning Book", "Andriy Burkov", "ML",
     "9781999579500", "Compact yet exhaustive summary of core machine learning algorithms, evaluation metrics, feature engineering, and production best practices.", 2019, "English", 4, 3),
    ("Machine Learning: A Probabilistic Perspective", "Kevin Murphy", "ML",
     "9780262018029", "In-depth probabilistic framework unifying supervised and unsupervised learning, Markov models, and variational inference.", 2012, "English", 2, 2),
    ("Introduction to Statistical Learning", "Gareth James et al.", "ML",
     "9781071614174", "Accessible statistical foundation for data science explaining linear models, cross-validation, regularization (Ridge/Lasso), and tree ensembles.", 2021, "English", 4, 3),

    # --- Deep Learning & GenAI ---
    ("Deep Learning", "Ian Goodfellow, Yoshua Bengio, Aaron Courville", "Deep Learning",
     "9780262035613", "The authoritative 'Deep Learning Bible' discussing feedforward networks, convolutional architectures, autoencoders, and generative adversarial networks (GANs).", 2016, "English", 4, 3),
    ("Deep Learning with Python", "François Chollet", "Deep Learning",
     "9781617294433", "Written by the creator of Keras. Offers an exceptionally clear introduction to building computer vision, sequence processing, and text generation models.", 2017, "English", 5, 4),
    ("Generative Deep Learning", "David Foster", "Deep Learning",
     "9781098134181", "Comprehensive guide on building generative models including VAEs, GANs, Diffusion Models, Transformers, and Large Language Models from scratch.", 2023, "English", 3, 2),
    ("Neural Networks and Deep Learning", "Michael Nielsen", "Deep Learning",
     "9781492037354", "Intuitive, first-principles exploration of backpropagation algorithm mechanics and handwritten digit classification using deep architectures.", 2019, "English", 2, 2),

    # --- NLP & Transformers ---
    ("Speech and Language Processing", "Jurafsky, Martin", "NLP",
     "9780131873216", "The premier NLP textbook covering n-grams, word embeddings, sequence labeling, attention mechanisms, modern LLMs, and conversational dialogue systems.", 2023, "English", 3, 2),
    ("Natural Language Processing with Python", "Bird, Klein, Loper", "NLP",
     "9780596516499", "Hands-on guide to computational linguistics using NLTK for tokenization, stemming, POS tagging, entity parsing, and corpus analysis.", 2009, "English", 3, 3),
    ("Natural Language Processing with Transformers", "Lewis Tunstall et al.", "NLP",
     "9781098103248", "Practical engineering manual for deploying HuggingFace Transformer models for text classification, named-entity recognition, and summarization pipelines.", 2022, "English", 4, 3),

    # --- Software Engineering & Architecture ---
    ("Clean Code", "Robert C. Martin", "Software Engineering",
     "9780132350884", "Iconic manifesto on writing human-readable, testable code. Details meaningful naming, single-responsibility functions, clean formatting, and refactoring techniques.", 2008, "English", 3, 0),
    ("The Pragmatic Programmer", "Andrew Hunt, David Thomas", "Software Engineering",
     "9780135957059", "Enduring principles of professional software development covering DRY, orthogonality, tracer bullets, debugging philosophies, and career wisdom.", 2019, "English", 3, 1),
    ("Design Patterns: Elements of Reusable Object-Oriented Software", "Gang of Four", "Software Engineering",
     "9780201633610", "The foundational catalog of 23 software design patterns categorized into Creational, Structural, and Behavioral solutions for robust system design.", 1994, "English", 3, 2),
    ("Refactoring: Improving the Design of Existing Code", "Martin Fowler", "Software Engineering",
     "9780134757599", "Definitive guide on identifying code smells and applying systematic, incremental transformations to improve code maintainability without altering external behavior.", 2018, "English", 2, 1),
    ("System Design Interview – An Insider's Guide", "Alex Xu", "Software Engineering",
     "9781736049112", "Step-by-step frameworks for designing scalable web services like YouTube, Twitter, distributed rate limiters, and key-value stores under immense traffic.", 2020, "English", 4, 0),
    ("Building Microservices", "Sam Newman", "Software Engineering",
     "9781492034025", "Practical architectural guide covering domain decomposition, asynchronous messaging, service mesh, decentralized data management, and CI/CD pipelines.", 2021, "English", 3, 2),
    ("Code Complete", "Steve McConnell", "Software Engineering",
     "9780735619678", "Comprehensive reference on software construction, defensive programming, defensive coding, variable scope control, and integration testing.", 2004, "English", 2, 1),

    # --- Python Programming ---
    ("Python Crash Course", "Eric Matthes", "Python",
     "9781593279288", "Fast-paced, hands-on introduction to Python programming covering syntax fundamentals, data visualization libraries, and full-stack web applications.", 2019, "English", 5, 4),
    ("Fluent Python", "Luciano Ramalho", "Python",
     "9781492056355", "Deep dive into Python's idiomatic features: special dunder methods, generator expressions, decorators, metaprogramming, and modern asyncio concurrency.", 2022, "English", 3, 2),
    ("Automate the Boring Stuff with Python", "Al Sweigart", "Python",
     "9781593279929", "Practical tutorial teaching programming through automating everyday office tasks: web scraping, Excel manipulation, PDF parsing, and email scheduling.", 2019, "English", 4, 3),
    ("Effective Python: 90 Specific Ways to Write Better Python", "Brett Slatkin", "Python",
     "9780134853987", "Item-by-item guide highlighting non-obvious Python idioms, generator patterns, metaclasses, and memory profiling techniques.", 2019, "English", 3, 2),

    # --- Java Programming ---
    ("Head First Java", "Kathy Sierra, Bert Bates", "Java",
     "9780596009205", "Visually engaging, conversational guide to Java covering object-oriented design, garbage collection, exceptions, collections, and multi-threaded programming.", 2005, "English", 3, 2),
    ("Effective Java", "Joshua Bloch", "Java",
     "9780134685991", "Best practices from a core Java platform designer. Covers builders, immutability, generics, enums, lambdas, streams, and defensive serialization.", 2018, "English", 3, 2),
    ("Java: The Complete Reference", "Herbert Schildt", "Java",
     "9781260440231", "Encyclopedic coverage of the Java standard library, concurrency utilities, NIO package, modules, and modern Java features.", 2021, "English", 2, 2),

    # --- Web Dev & JavaScript ---
    ("HTML and CSS: Design and Build Websites", "Jon Duckett", "Web Dev",
     "9781118008188", "Visually structured design handbook introducing HTML5 structure, semantic tags, modern CSS layout techniques, and responsive web styling.", 2011, "English", 4, 3),
    ("JavaScript: The Good Parts", "Douglas Crockford", "Web Dev",
     "9780596517748", "Crisp analysis of JavaScript's elegant functional design: functions as first-class citizens, lexical closures, and prototypal inheritance.", 2008, "English", 3, 2),
    ("Eloquent JavaScript", "Marijn Haverbeke", "Web Dev",
     "9781593279509", "Thoughtful deep dive into modern JavaScript, browser DOM manipulation, Node.js runtime, asynchronous event loops, and clean coding paradigms.", 2018, "English", 3, 2),
    ("Node.js Design Patterns", "Mario Casciaro, Luciano Mammino", "Web Dev",
     "9781839214110", "Advanced architectural patterns for asynchronous backends using event emitters, streams, worker threads, and scalable microservices in Node.js.", 2020, "English", 2, 1),

    # --- Cloud & DevOps ---
    ("The Phoenix Project", "Gene Kim, Kevin Behr, George Spafford", "Cloud",
     "9780988262591", "Engaging business novel illustrating DevOps principles, the Three Ways, flow optimization, and cross-functional collaboration in IT organizations.", 2013, "English", 4, 3),
    ("Site Reliability Engineering", "Niall Richard Murphy et al.", "Cloud",
     "9781491929124", "Google's internal practices on running production systems at scale: error budgets, SLOs/SLAs, incident response, monitoring, and eliminating toil.", 2016, "English", 3, 2),
    ("Kubernetes in Action", "Marko Luksa", "Cloud",
     "9781617293726", "Comprehensive guide to container orchestration, Pod lifecycles, Deployments, StatefulSets, networking ingress, and Helm configurations.", 2018, "English", 3, 2),

    # --- Cybersecurity ---
    ("The Web Application Hacker's Handbook", "Dafydd Stuttard, Marcus Pinto", "Cybersecurity",
     "9781118026472", "The bible of web security covering injection attacks, session flaws, authentication bypasses, CSRF, and practical defense countermeasures.", 2011, "English", 3, 2),
    ("Practical Malware Analysis", "Michael Sikorski, Andrew Honig", "Cybersecurity",
     "9781593272906", "Hands-on guide to dissecting malicious binaries using static analysis, x86 disassembly with IDA Pro, and dynamic debugging techniques.", 2012, "English", 2, 1),
    ("Hacking: The Art of Exploitation", "Jon Erickson", "Cybersecurity",
     "9781593271442", "Fundamentals of security vulnerability exploitation covering C buffer overflows, network sniffing, cryptanalysis, and shellcode writing.", 2008, "English", 2, 1),

    # --- Mathematics ---
    ("Discrete Mathematics and Its Applications", "Kenneth H. Rosen", "Maths",
     "9780073383095", "The standard curriculum textbook covering formal logic, boolean algebra, induction, combinatorics, graph theory, and discrete probability.", 2018, "English", 4, 3),
    ("Linear Algebra Done Right", "Sheldon Axler", "Maths",
     "9783319110790", "Elegant mathematical approach highlighting vector spaces, linear transformations, and spectral theorems without determinants.", 2015, "English", 3, 2),
    ("Probability and Statistics for Engineering", "Jay L. Devore", "Maths",
     "9781305251809", "Foundational probability distributions, hypothesis testing, ANOVA, and regression models designed for engineering research.", 2015, "English", 3, 2),
    ("Calculus: Early Transcendentals", "James Stewart", "Maths",
     "9781285741550", "The premier undergraduate calculus text covering limits, multivariable derivatives, partial differentiation, and multiple integrals.", 2015, "English", 3, 3),
    ("Naked Statistics", "Charles Wheelan", "Maths",
     "9780393347777", "Stripping the dread from data, explaining regression analysis, central limit theorem, and correlation with witty real-world anecdotes.", 2013, "English", 3, 2),

    # --- Self-Help & Personal Growth ---
    ("Atomic Habits", "James Clear", "Self-help",
     "9780735211292", "Actionable framework for building lasting micro-habits through the 4 laws of behavior change: cue, craving, response, and reward.", 2018, "English", 5, 4),
    ("Deep Work", "Cal Newport", "Self-help",
     "9781455586691", "Compelling rules for focused, distraction-free concentration in a noisy modern world, cultivating high-value intellectual output.", 2016, "English", 4, 3),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "Self-help",
     "9780374533557", "Nobel laureate's groundbreaking work exploring System 1 intuitive thinking versus System 2 deliberate analytical reasoning and cognitive biases.", 2011, "English", 3, 2),
    ("Make It Stick: The Science of Successful Learning", "Peter C. Brown et al.", "Self-help",
     "9780674729018", "Cognitive psychology insights proving that retrieval practice, spaced repetition, and interleaving drastically enhance memory retention.", 2014, "English", 3, 2),
    ("So Good They Can't Ignore You", "Cal Newport", "Self-help",
     "9781455509126", "Debunks the 'follow your passion' myth, arguing that building rare and valuable career capital is what creates true job satisfaction.", 2012, "English", 3, 2),
    ("The 7 Habits of Highly Effective People", "Stephen R. Covey", "Self-help",
     "9780743269513", "Holistic character-based approach for personal and professional effectiveness focused on proactivity, paradigms, and win-win thinking.", 1989, "English", 3, 2),

    # --- Fiction & Science Fiction ---
    ("Project Hail Mary", "Andy Weir", "Fiction",
     "9780593135204", "Riveting interstellar survival story following a sole astronaut solving physics and biology problems to save humanity from extinction.", 2021, "English", 3, 2),
    ("1984", "George Orwell", "Fiction",
     "9780451524935", "Classic dystopian novel portraying life under relentless totalitarian surveillance, propaganda, and thought-police control in Oceania.", 1949, "English", 4, 3),
    ("Dune", "Frank Herbert", "Fiction",
     "9780441172719", "Epic science fiction saga of Paul Atreides navigating desert ecology, spice trade politics, mysticism, and empire betrayal on Arrakis.", 1965, "English", 3, 2),
    ("The Hitchhiker's Guide to the Galaxy", "Douglas Adams", "Fiction",
     "9780345391803", "Wildly humorous comic space journey following Arthur Dent after Earth is unexpectedly demolished for a hyperspace bypass.", 1979, "English", 3, 2),
    ("Surely You're Joking, Mr. Feynman!", "Richard P. Feynman", "Fiction",
     "9780393316049", "Hilarious, inspiring adventures and autobiographical reflections of the legendary Nobel laureate physicist and safecracker.", 1985, "English", 3, 2),

    # --- Reference (In-Library Use Only) ---
    ("Oxford Dictionary of Computer Science", "Andrew Butterfield et al.", "Reference",
     "9780199688975", "Authoritative reference providing clear, concise definitions for over 6,500 core terms across algorithms, security, and hardware.", 2016, "English", 2, 2),
    ("Encyclopedia of Machine Learning and Data Mining", "Claude Sammut, Geoffrey I. Webb", "Reference",
     "9781489976857", "Comprehensive peer-reviewed compendium documenting theoretical foundations, algorithms, and applications of machine learning.", 2017, "English", 1, 1),
]

cur.executemany(
    """INSERT INTO books
       (title, author, subject, isbn, description, published_year, language, total_copies, available_copies)
       VALUES (?,?,?,?,?,?,?,?,?)""",
    books,
)
conn.commit()

# ---------------------------------------------------------------------------
# 3. Members (18 Students across Departments)
# ---------------------------------------------------------------------------
members = [
    ("Arjun Sharma",    "arjun.sharma@college.edu",   "CSE", 2, td(-420)),
    ("Priya Nair",      "priya.nair@college.edu",     "CSE", 3, td(-410)),
    ("Rahul Verma",     "rahul.verma@college.edu",    "ISE", 2, td(-400)),
    ("Sneha Iyer",      "sneha.iyer@college.edu",     "ECE", 3, td(-390)),
    ("Vikram Patel",    "vikram.patel@college.edu",   "CSE", 4, td(-380)),
    ("Meera Krishnan",  "meera.krishnan@college.edu", "ISE", 3, td(-370)),
    ("Aditya Rao",      "aditya.rao@college.edu",     "ECE", 2, td(-360)),
    ("Kavya Menon",     "kavya.menon@college.edu",    "CSE", 1, td(-350)),
    ("Rohan Kulkarni",  "rohan.kulkarni@college.edu", "AI&DS", 2, td(-300)),
    ("Ananya Deshmukh", "ananya.d@college.edu",       "AI&DS", 3, td(-290)),
    ("Siddharth Gupta", "sid.gupta@college.edu",      "CSE", 3, td(-280)),
    ("Ishaan Sen",      "ishaan.sen@college.edu",     "Mech", 2, td(-270)),
    ("Divya Balan",     "divya.balan@college.edu",    "ECE", 4, td(-260)),
    ("Tanvi Joshi",     "tanvi.joshi@college.edu",    "ISE", 2, td(-250)),
    ("Varun Bhat",      "varun.bhat@college.edu",     "AI&DS", 1, td(-200)),
    ("Pooja Hegde",     "pooja.hegde@college.edu",    "Biotech", 3, td(-190)),
    ("Karthik Reddy",   "karthik.r@college.edu",      "Civil", 2, td(-180)),
    ("Neha Saxena",     "neha.saxena@college.edu",    "CSE", 4, td(-170)),
]

cur.executemany(
    "INSERT INTO members (name, email, department, year, joined_on) VALUES (?,?,?,?,?)",
    members,
)
conn.commit()

# ---------------------------------------------------------------------------
# 4. Realistic Loans (Active, Returned, and Overdue)
# ---------------------------------------------------------------------------
def issue_loan(member_id, book_id, issued_on_days, due_days, returned_on_days=None,
               renewed=0, fine_amount=0, fine_paid=0):
    issued_on = td(issued_on_days)
    due_on = td(due_days)
    returned_on = td(returned_on_days) if returned_on_days is not None else None

    cur.execute(
        """INSERT INTO loans
           (member_id, book_id, issued_on, due_on, returned_on, renewed_count, fine_amount, fine_paid)
           VALUES (?,?,?,?,?,?,?,?)""",
        (member_id, book_id, issued_on, due_on, returned_on, renewed, fine_amount, fine_paid),
    )
    if returned_on is None:
        cur.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
            (book_id,),
        )

# Past returned loans
issue_loan(1, 1, -30, -16, -15)
issue_loan(2, 7, -25, -11, -10)
issue_loan(3, 9, -20, -6, -5)
issue_loan(3, 3, -15, -1, -2)
issue_loan(4, 15, -18, -4, -3)
issue_loan(5, 20, -40, -26, -25)
issue_loan(6, 25, -35, -21, -20)
issue_loan(7, 35, -22, -8, -7)
issue_loan(8, 55, -28, -14, -13)
issue_loan(9, 21, -19, -5, -4)
issue_loan(10, 26, -14, 0, 0)
issue_loan(11, 40, -32, -18, -17)

# Active on-time loans
issue_loan(1, 19, -10, 4)
issue_loan(1, 30, -8, 6)
issue_loan(2, 39, -5, 9)
issue_loan(2, 57, -7, 7)
issue_loan(3, 27, -3, 11)
issue_loan(4, 41, -6, 8)
issue_loan(5, 56, -4, 10)
issue_loan(6, 11, -2, 12)
issue_loan(9, 22, -4, 10)
issue_loan(10, 28, -3, 11)
issue_loan(11, 36, -5, 9)
issue_loan(12, 58, -7, 7)

# Overdue loans (between 3 and 20 days late)
issue_loan(1, 7,  -24, -10)
issue_loan(2, 23, -27, -13)
issue_loan(3, 12, -20, -17)
issue_loan(4, 17, -22, -19)
issue_loan(7, 34, -20,  -3)
issue_loan(8, 43, -34, -20)
issue_loan(13, 8, -25, -11)
issue_loan(14, 18, -22, -8)

conn.commit()

# Ensure 0-copy books are clean
cur.execute("UPDATE books SET available_copies = 0 WHERE title IN ('Clean Code', 'System Design Interview – An Insider''s Guide', 'Designing Data-Intensive Applications')")
cur.execute("UPDATE books SET available_copies = 0 WHERE available_copies < 0")
conn.commit()

# ---------------------------------------------------------------------------
# 5. Reservations (Active on out-of-stock books)
# ---------------------------------------------------------------------------
# Find book IDs for 0-copy books
cur.execute("SELECT id, title FROM books WHERE available_copies = 0")
zero_books = {r["title"]: r["id"] for r in cur.fetchall()}

clean_code_id = zero_books.get("Clean Code", 32)
sys_design_id = zero_books.get("System Design Interview – An Insider's Guide", 36)
ddia_id = zero_books.get("Designing Data-Intensive Applications", 14)

cur.execute("INSERT INTO reservations (member_id, book_id, reserved_on, status) VALUES (?,?,?,?)", (6, clean_code_id, td(-2), "active"))
cur.execute("INSERT INTO reservations (member_id, book_id, reserved_on, status) VALUES (?,?,?,?)", (7, clean_code_id, td(-1), "active"))
cur.execute("INSERT INTO reservations (member_id, book_id, reserved_on, status) VALUES (?,?,?,?)", (9, sys_design_id, td(-3), "active"))
cur.execute("INSERT INTO reservations (member_id, book_id, reserved_on, status) VALUES (?,?,?,?)", (10, ddia_id, td(-1), "active"))

conn.commit()
conn.close()

# ---------------------------------------------------------------------------
# 6. Rebuild Vector Indexes
# ---------------------------------------------------------------------------
print("Embedding books and policies into ChromaDB...")
from rag import index_books, index_policies
index_books()
index_policies()

# ---------------------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------------------
conn2 = get_conn()
b_cnt = conn2.execute("SELECT COUNT(*) FROM books").fetchone()[0]
m_cnt = conn2.execute("SELECT COUNT(*) FROM members").fetchone()[0]
l_cnt = conn2.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
act_l = conn2.execute("SELECT COUNT(*) FROM loans WHERE returned_on IS NULL").fetchone()[0]
ovr_l = conn2.execute("SELECT COUNT(*) FROM loans WHERE returned_on IS NULL AND due_on < ?", (TODAY.isoformat(),)).fetchone()[0]
res_c = conn2.execute("SELECT COUNT(*) FROM reservations WHERE status='active'").fetchone()[0]
conn2.close()

print(f"✅ Seeding Complete!")
print(f"   Total Books:        {b_cnt}")
print(f"   Registered Members: {m_cnt}")
print(f"   Total Loans:        {l_cnt} (Active: {act_l}, Overdue: {ovr_l})")
print(f"   Reservations:       {res_c}")
