// ABOUTME: Seed data for Lockin — creates a realistic demo browsing session
// ABOUTME: Run this after Neo4j starts to populate the graph with mock data

// Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (si:Site) REQUIRE si.domain IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (v:Visit) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Task) REQUIRE t.name IS UNIQUE;

// Session + Task
CREATE (s:Session {id: 'demo-session-001', task: 'Fix auth bug in login flow', start_time: datetime('2026-04-02T10:00:00'), end_time: datetime('2026-04-02T11:30:00'), status: 'completed'})
CREATE (t:Task {name: 'Fix auth bug in login flow', created_at: datetime('2026-04-02T10:00:00')})
CREATE (s)-[:HAS_TASK]->(t)

// Sites with classifications
CREATE (s1:Site {domain: 'docs.auth0.com', classification: 'on_task', classified_by: 'llm', first_seen: datetime('2026-04-02T10:00:00')})
CREATE (s2:Site {domain: 'stackoverflow.com', classification: 'on_task', classified_by: 'llm', first_seen: datetime('2026-04-02T10:05:00')})
CREATE (s3:Site {domain: 'github.com', classification: 'on_task', classified_by: 'llm', first_seen: datetime('2026-04-02T10:15:00')})
CREATE (s4:Site {domain: 'reddit.com', classification: 'distraction', classified_by: 'llm', first_seen: datetime('2026-04-02T10:22:00')})
CREATE (s5:Site {domain: 'youtube.com', classification: 'distraction', classified_by: 'llm', first_seen: datetime('2026-04-02T10:35:00')})
CREATE (s6:Site {domain: 'twitter.com', classification: 'distraction', classified_by: 'llm', first_seen: datetime('2026-04-02T11:00:00')})
CREATE (s7:Site {domain: 'jwt.io', classification: 'on_task', classified_by: 'llm', first_seen: datetime('2026-04-02T10:42:00')})

// Task classification relationships
CREATE (s1)-[:ON_TASK_FOR]->(t)
CREATE (s2)-[:ON_TASK_FOR]->(t)
CREATE (s3)-[:ON_TASK_FOR]->(t)
CREATE (s7)-[:ON_TASK_FOR]->(t)
CREATE (s4)-[:DISTRACTION_FROM]->(t)
CREATE (s5)-[:DISTRACTION_FROM]->(t)
CREATE (s6)-[:DISTRACTION_FROM]->(t)

// Visits (realistic browsing sequence)
CREATE (v1:Visit {id: 'v001', url: 'https://docs.auth0.com/docs/quickstart', title: 'Auth0 Quickstart', start_time: datetime('2026-04-02T10:00:00'), duration_seconds: 300, active: true})
CREATE (v2:Visit {id: 'v002', url: 'https://stackoverflow.com/questions/auth-jwt-refresh', title: 'JWT refresh token best practices', start_time: datetime('2026-04-02T10:05:00'), duration_seconds: 600, active: true})
CREATE (v3:Visit {id: 'v003', url: 'https://github.com/myorg/myrepo/pull/42', title: 'PR #42 - Auth middleware refactor', start_time: datetime('2026-04-02T10:15:00'), duration_seconds: 420, active: true})
CREATE (v4:Visit {id: 'v004', url: 'https://reddit.com/r/programming', title: 'r/programming', start_time: datetime('2026-04-02T10:22:00'), duration_seconds: 780, active: true})
CREATE (v5:Visit {id: 'v005', url: 'https://youtube.com/watch?v=dQw4w9WgXcQ', title: 'Random video', start_time: datetime('2026-04-02T10:35:00'), duration_seconds: 420, active: false})
CREATE (v6:Visit {id: 'v006', url: 'https://jwt.io/', title: 'JWT.io Debugger', start_time: datetime('2026-04-02T10:42:00'), duration_seconds: 900, active: true})
CREATE (v7:Visit {id: 'v007', url: 'https://docs.auth0.com/docs/tokens', title: 'Auth0 Token Docs', start_time: datetime('2026-04-02T10:57:00'), duration_seconds: 180, active: true})
CREATE (v8:Visit {id: 'v008', url: 'https://twitter.com/home', title: 'Twitter Home', start_time: datetime('2026-04-02T11:00:00'), duration_seconds: 480, active: true})
CREATE (v9:Visit {id: 'v009', url: 'https://github.com/myorg/myrepo/pull/42/files', title: 'PR #42 Files Changed', start_time: datetime('2026-04-02T11:08:00'), duration_seconds: 1320, active: true})

// Visit → Site relationships
CREATE (v1)-[:TO_SITE]->(s1)
CREATE (v2)-[:TO_SITE]->(s2)
CREATE (v3)-[:TO_SITE]->(s3)
CREATE (v4)-[:TO_SITE]->(s4)
CREATE (v5)-[:TO_SITE]->(s5)
CREATE (v6)-[:TO_SITE]->(s7)
CREATE (v7)-[:TO_SITE]->(s1)
CREATE (v8)-[:TO_SITE]->(s6)
CREATE (v9)-[:TO_SITE]->(s3)

// Session → Visit relationships
CREATE (s)-[:CONTAINS]->(v1)
CREATE (s)-[:CONTAINS]->(v2)
CREATE (s)-[:CONTAINS]->(v3)
CREATE (s)-[:CONTAINS]->(v4)
CREATE (s)-[:CONTAINS]->(v5)
CREATE (s)-[:CONTAINS]->(v6)
CREATE (s)-[:CONTAINS]->(v7)
CREATE (s)-[:CONTAINS]->(v8)
CREATE (s)-[:CONTAINS]->(v9)

// Temporal sequence
CREATE (v1)-[:NEXT]->(v2)
CREATE (v2)-[:NEXT]->(v3)
CREATE (v3)-[:NEXT]->(v4)
CREATE (v4)-[:NEXT]->(v5)
CREATE (v5)-[:NEXT]->(v6)
CREATE (v6)-[:NEXT]->(v7)
CREATE (v7)-[:NEXT]->(v8)
CREATE (v8)-[:NEXT]->(v9)
