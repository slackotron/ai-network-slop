# Create auditor instance
auditor = AristaConfigAuditor()

# Run full audit
results = auditor.run_audit()

# Save results to file
auditor.save_results(results)



single
config = "... device config ..."
findings = auditor.audit_config(config)
