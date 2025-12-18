# ActorHub.ai - Production Advancement Plan

> **Objective:** Advance from Early Beta to Production-Ready in 90 Days
> **Date:** 2025-12-18
> **Role:** Principal Engineer + Product Owner

---

## Executive Summary

### Current State Assessment

| Category | Score | Status |
|----------|-------|--------|
| Core Backend | 85/100 | LoRA, Quality, Motion implemented |
| Database & Models | 90/100 | All tables exist, migrations ready |
| API Endpoints | 85/100 | Admin, Notifications, Subscriptions added |
| Frontend | 55/100 | Missing 8+ critical pages |
| Testing | 45/100 | ~11 test files, needs integration/E2E |
| Infrastructure | 75/100 | Docker/CI ready, K8s/Terraform empty |
| Security | 80/100 | Admin protection, audit logging done |

### Production Definition

**"Production-Ready" means:**
1. A real customer can register, train an Actor Pack, and receive a usable model
2. A buyer can purchase a license and download content legally
3. A creator can receive real money via payouts
4. The system survives 100 concurrent users without degradation
5. All errors are logged, monitored, and alertable
6. Data is backed up and recoverable within 4 hours

---

## Phase 1: Core Completion (Days 1-30)

### Week 1-2: Backend Hardening

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Add voice cloning fallback (XTTS/Coqui) | P1 | 3 days | Backend |
| Implement refund handling endpoint | P1 | 2 days | Backend |
| Add analytics/reporting endpoints | P1 | 3 days | Backend |
| Complete webhook event persistence | P2 | 1 day | Backend |
| Add request size limits middleware | P2 | 1 day | Backend |

**Deliverables:**
- [ ] `/api/v1/refunds` endpoint with Stripe integration
- [ ] `/api/v1/analytics/usage` and `/api/v1/analytics/revenue` endpoints
- [ ] Voice cloning graceful degradation to XTTS
- [ ] Request body size validation (50MB limit)

### Week 3-4: Frontend Critical Pages

| Page | Route | Priority | Effort |
|------|-------|----------|--------|
| Identity Detail | `/identity/[id]` | P0 | 3 days |
| Identity Edit | `/identity/[id]/edit` | P0 | 2 days |
| License Management | `/licenses` | P0 | 3 days |
| Usage Analytics | `/dashboard/analytics` | P1 | 4 days |
| Notification Center | `/notifications` | P1 | 2 days |
| Payout Settings | `/settings/payouts` | P1 | 3 days |

**Deliverables:**
- [ ] Identity detail page with training status, verifications, earnings
- [ ] Identity edit form with validation
- [ ] License list with filtering, status indicators
- [ ] Analytics dashboard with Recharts (usage, revenue, verifications)
- [ ] Full notification center with read/unread, filtering
- [ ] Payout settings with bank account management

---

## Phase 2: Testing & Quality (Days 31-60)

### Week 5-6: Backend Test Coverage

| Test Suite | Current | Target | Effort |
|------------|---------|--------|--------|
| Unit Tests | ~40% | 80% | 5 days |
| Integration Tests | ~10% | 60% | 5 days |
| E2E API Tests | 0% | 100% critical | 4 days |

**Required Test Files:**
```
tests/
├── unit/
│   ├── test_training_pipeline.py      # LoRA, quality, motion
│   ├── test_payment_processing.py     # Stripe flows
│   ├── test_webhook_handlers.py       # Idempotency
│   └── test_rate_limiting.py          # Rate limit logic
├── integration/
│   ├── test_identity_lifecycle.py     # Register → Train → Verify
│   ├── test_license_purchase.py       # Browse → Buy → Download
│   ├── test_payout_flow.py            # Earn → Request → Receive
│   └── test_subscription_lifecycle.py # Subscribe → Use → Cancel
└── e2e/
    ├── test_customer_journey.py       # Full buyer flow
    └── test_creator_journey.py        # Full creator flow
```

### Week 7-8: Frontend Testing

| Test Type | Target | Effort |
|-----------|--------|--------|
| Component Tests | 50% | 4 days |
| Playwright E2E | 10 critical flows | 5 days |
| Visual Regression | Key pages | 2 days |

**Critical E2E Flows:**
1. User registration → Email verification → Dashboard
2. Identity creation → Photo upload → Training start
3. Marketplace browse → License purchase → Download
4. Settings → API key creation → API call
5. Notification received → Read → Action taken

---

## Phase 3: Infrastructure & Security (Days 61-90)

### Week 9-10: Kubernetes & IaC

| Task | Priority | Effort |
|------|----------|--------|
| Kubernetes manifests (API, Web, Worker) | P0 | 4 days |
| Terraform AWS infrastructure | P0 | 5 days |
| Auto-scaling configuration | P1 | 2 days |
| CDN setup (CloudFront) | P1 | 1 day |
| Database backup automation | P0 | 2 days |

**Kubernetes Deliverables:**
```
infrastructure/kubernetes/
├── namespace.yaml
├── configmaps/
├── secrets/
├── deployments/
│   ├── api.yaml
│   ├── web.yaml
│   └── worker.yaml
├── services/
├── ingress/
├── hpa/                    # Horizontal Pod Autoscaler
└── pdb/                    # Pod Disruption Budget
```

**Terraform Deliverables:**
```
infrastructure/terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── vpc/
│   ├── ecs/
│   ├── rds/
│   ├── elasticache/
│   ├── s3/
│   └── cloudfront/
└── environments/
    ├── staging/
    └── production/
```

### Week 11-12: Security & Compliance

| Task | Priority | Effort |
|------|----------|--------|
| Brute force protection (login) | P0 | 1 day |
| Input sanitization audit | P0 | 2 days |
| GDPR data export automation | P1 | 2 days |
| Terms acceptance tracking | P1 | 1 day |
| Security penetration test | P0 | 3 days |
| Load testing (100 users) | P0 | 2 days |

**Security Deliverables:**
- [ ] Login rate limit: 5 attempts per 15 minutes
- [ ] Account lockout after 10 failed attempts
- [ ] Automated GDPR data export within 48 hours
- [ ] Load test report: p95 < 500ms at 100 concurrent users
- [ ] Penetration test report with zero critical findings

---

## Risk Register

| ID | Risk | Impact | Probability | Mitigation | Owner |
|----|------|--------|-------------|------------|-------|
| R1 | Replicate API rate limits | High | Medium | Implement queue, add fallback provider | Backend |
| R2 | ElevenLabs quota exceeded | High | Medium | XTTS fallback already planned | Backend |
| R3 | Stripe webhook failures | Critical | Low | Idempotency implemented, add retry queue | Backend |
| R4 | Training takes >1 hour | Medium | High | Set user expectations, background jobs | Product |
| R5 | Database scaling issues | High | Medium | Read replicas, connection pooling | DevOps |
| R6 | S3 storage costs spike | Medium | Medium | Set quotas per tier, compress uploads | DevOps |
| R7 | GDPR compliance gap | Critical | Low | Audit complete, add automation | Legal |
| R8 | DDoS attack | Critical | Medium | CloudFront + WAF, rate limiting exists | DevOps |
| R9 | Key rotation failure | High | Low | Automated secret rotation, alerts | DevOps |
| R10 | Team bandwidth | High | High | Prioritize ruthlessly, no new features | PM |

---

## Go/No-Go Checklist

### Must Have (Go Blockers)

**Core Functionality:**
- [ ] User can register and verify email
- [ ] User can upload photos and start training
- [ ] Training produces downloadable LoRA model
- [ ] Quality scores are real (not mocked)
- [ ] Voice cloning works or gracefully degrades
- [ ] Motion capture returns real pose data

**Marketplace:**
- [ ] Listings display with correct pricing
- [ ] License purchase completes via Stripe
- [ ] Purchased content is downloadable
- [ ] Creator receives payout notification

**Infrastructure:**
- [ ] Zero critical security vulnerabilities
- [ ] Database backups verified and tested
- [ ] Monitoring alerts configured and tested
- [ ] Health endpoints return accurate status
- [ ] SSL certificates valid and auto-renewing

**Compliance:**
- [ ] Terms of Service accepted before registration
- [ ] Privacy policy accessible
- [ ] GDPR data export functional
- [ ] Age verification for adult content

### Should Have (Soft Launch Acceptable Without)

- [ ] Analytics dashboard fully populated
- [ ] Notification center complete
- [ ] Full API key management UI
- [ ] Mobile-responsive polish
- [ ] Multi-language support

### Nice to Have (Post-Launch)

- [ ] Real-time training progress
- [ ] Bulk operations
- [ ] Advanced search/filtering
- [ ] Social features (follows, shares)
- [ ] Referral program

---

## 90-Day Timeline

```
Week 1-2:   ████████ Backend Hardening
Week 3-4:   ████████ Frontend Critical Pages
Week 5-6:   ████████ Backend Testing (80%)
Week 7-8:   ████████ Frontend Testing + E2E
Week 9-10:  ████████ Kubernetes + Terraform
Week 11-12: ████████ Security + Load Testing

Day 85:     -------- Staging Freeze
Day 87:     -------- Security Audit Complete
Day 89:     -------- Go/No-Go Decision
Day 90:     -------- Production Launch Window
```

---

## Success Metrics

| Metric | Current | Target (Day 90) |
|--------|---------|-----------------|
| Backend Test Coverage | ~45% | ≥80% |
| Frontend Test Coverage | ~10% | ≥50% |
| Critical E2E Tests | 0 | 10+ passing |
| API p95 Latency | Unknown | <500ms |
| Uptime (30-day) | N/A | ≥99.5% |
| Error Rate | Unknown | <1% |
| Security Vulns (Critical) | Unknown | 0 |
| GDPR Compliance | Partial | 100% |

---

## Team Allocation (Recommended)

| Role | Allocation | Focus |
|------|------------|-------|
| Backend Engineer 1 | 100% | Core services, testing |
| Backend Engineer 2 | 100% | Integrations, webhooks |
| Frontend Engineer 1 | 100% | Critical pages |
| Frontend Engineer 2 | 50% | Testing, polish |
| DevOps Engineer | 100% | K8s, Terraform, monitoring |
| QA Engineer | 100% | E2E testing, load testing |
| Security Consultant | 25% | Audit, penetration testing |

---

## Constraints (Non-Negotiable)

1. **No new features** beyond this scope
2. **No blockchain** integration
3. **No GraphQL** - REST only
4. **No UI polish** without backend support
5. **Every feature must be testable**
6. **Every endpoint must be documented**

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2025-12-18 | Use Replicate for LoRA | Fastest to production | Cost: ~$0.50/training |
| 2025-12-18 | MediaPipe for motion | Free, runs locally | CPU overhead acceptable |
| 2025-12-18 | Keep ElevenLabs primary | Best quality | Add XTTS fallback |
| 2025-12-18 | ECS over EKS for launch | Simpler, faster | Migrate to K8s post-launch |

---

## Appendix: File Locations

**Backend Core:**
- Training Service: `apps/api/app/services/training.py`
- Models: `apps/api/app/models/`
- Endpoints: `apps/api/app/api/v1/endpoints/`
- Tests: `apps/api/tests/`

**Frontend Core:**
- Pages: `apps/web/src/app/`
- Components: `apps/web/src/components/`
- API Client: `apps/web/src/lib/api.ts`

**Infrastructure:**
- Docker: `docker-compose.*.yml`
- CI/CD: `.github/workflows/`
- Monitoring: `infrastructure/monitoring/`
- K8s (empty): `infrastructure/kubernetes/`
- Terraform (empty): `infrastructure/terraform/`

---

*Document Version: 1.0*
*Last Updated: 2025-12-18*
*Next Review: Weekly during 90-day sprint*
