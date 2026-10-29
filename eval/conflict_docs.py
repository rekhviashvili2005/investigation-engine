DOCS = [
    # --- წინააღმდეგობა 1: Zorvex-ის ინციდენტის მიზეზი ---
    ("Zorvex payments outage, March 12 2024: engineering postmortem",
     "synthetic://zorvex-postmortem-a",
     "On March 12 2024 the Zorvex payment processing service was unavailable for 94 minutes. "
     "The root cause was a faulty database schema migration deployed at 09:10 UTC to the ledger cluster. "
     "The migration locked the transactions table and caused the payment-gateway service to time out. "
     "Engineers rolled back the migration at 10:44 UTC and service was restored."),
    ("Zorvex March 12 2024 incident: customer summary",
     "synthetic://zorvex-postmortem-b",
     "Zorvex payments were down on March 12 2024 for roughly 94 minutes. "
     "According to this summary the outage was caused by an expired TLS certificate on the "
     "payment-gateway load balancer. The certificate was renewed at 10:44 UTC and the service recovered."),

    # --- წინააღმდეგობა 2: Quillon-ის დაზიანებული სერვისი ---
    ("Quillon outage report, June 3 2024: internal review",
     "synthetic://quillon-report-a",
     "On June 3 2024 Quillon experienced a 40 minute outage. The failure originated in the "
     "authentication service, which ran out of connection pool slots after a traffic spike. "
     "No other services were affected."),
    ("Quillon June 3 2024 incident notice",
     "synthetic://quillon-report-b",
     "The June 3 2024 Quillon incident lasted 40 minutes. The failing component was the search "
     "indexing service, which stopped accepting writes. The authentication service remained healthy "
     "throughout the incident."),

    # --- კონტროლი: Brannet-ის ორი ანგარიში თანხმდება ---
    ("Brannet checkout degradation, August 20 2024: engineering report",
     "synthetic://brannet-report-a",
     "On August 20 2024 Brannet checkout was degraded for 55 minutes. The cause was a misconfigured "
     "cache eviction policy deployed to the cart service, which overloaded the primary database."),
    ("Brannet August 20 2024 checkout incident: status summary",
     "synthetic://brannet-report-b",
     "Brannet's checkout slowdown on August 20 2024 lasted about 55 minutes. It was triggered by a "
     "cache eviction policy misconfiguration in the cart service that put excessive load on the "
     "primary database."),
]

# (question, expected_status, expected_keyword)
QUESTIONS = [
    ("What caused the Zorvex payments outage on March 12 2024?", "conflict", None),
    ("Which Quillon service failed during the June 3 2024 outage?", "conflict", None),
    ("What caused the Brannet checkout degradation on August 20 2024?", "answered", "cache"),
]