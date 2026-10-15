# Deployment and release readiness

This is the current acceptance checklist, not the old trial-account plan.
[Status](../status.md) records implementation gaps;
[verification history](../verification/history.md) records dated account evidence.
No profile is production-ready today.

| Gate | Required evidence | Delivery owners |
| --- | --- | --- |
| Product/release scope | Approved users, entity types, first jurisdictions, license and named responsibilities | TS-035/036 |
| Profile capability | Geography, identity, runtime/packages, transactional/object storage, egress, source rights, secrets and costs | TS-025/038/039/050 |
| Repeatable install | Reviewed plan/apply, ordered migrations, clean install, partial-install recovery, upgrade and preserved data | TS-029/037/038 |
| Durable research | Identity gate, all enabled branches, retained evidence/readback, normalized replay, failures and one execution owner | TS-002/003/008/026 |
| Claim/assessment quality | Labeled evaluation, supported claims, explicit eligibility and approved versioned scoring if enabled | TS-018/019/020 |
| Connected review | Durable authorized commands, snapshot/version/idempotency checks, readback and reconnect | TS-004/005/021/022/027/047 |
| Operations | Bounded quotas, measured targets, effective access, notification delivery, cancellation, restore and incident ownership | TS-025/034/040/041/042/043 |
| Optional capabilities | Separate source/access/evaluation acceptance for AI, documents, monitoring and integrations | TS-009/023/024/028/044/045/046/049 |

Dependencies in the [manifest](../backlog/index.json) determine execution order.
These gates group evidence; they do not create another backlog or deadline.

For the direct configured Google profile, bind a trusted installation/operator and
restrict access. Product signup/multi-user membership remains a separate later gate;
a single-operator slice does not satisfy production tenant authorization criteria.

Use synthetic fixtures for offline contracts and real retained captures for replay.
An approved live slice must show source retrieval, original evidence/hash readback,
identity, specialist outputs, comparison/validation, explicit unscored assessment
and durable review. Record commit/image/migration versions, commands and limitations.

Before activation, inspect actual account/project, grants, package/feature availability,
source access, residency, quota and notification configuration. Templates and metadata
settings do not prove executable services. Keep schedules inactive until their gates
pass; cloud apply and recurring spend are separate operations from plan generation.
