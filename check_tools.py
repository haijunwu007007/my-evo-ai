import sys, json
sys.path.insert(0, 'api')
from agent_tools import list_tools, _tools
t = list_tools()
print(f"Total: {len(t)}")
names = {x['name'] for x in t}

# All 86 expected tool names from the user's list
expected = [
    "browser_automate","deep_research","fullstack_project","memory_save","memory_search",
    "external_tools","code_analyze","skill_learn","desktop_automation","api_discover",
    "markdown_convert","web_scrape","computer_control","screenshot_to_code","code_review",
    "generate_test","code_edit","messaging_platform","voice_synth","multi_agent",
    "autonomous_task","fix_issue","create_project","nl_query_db","create_webapp",
    "agent_eval","video_script","chart_create","ocr_image","extract_pdf",
    "security_scan","code_audit","contract_review","crm_contacts","create_invoice",
    "create_ticket","send_social","send_email","bi_report","survey_create",
    "document_extraction","legal_agreement","claude_code","employee_lookup","dashboard",
    "expense_record","project_manage","erp_manage","ai_erp","schedule_add",
    "send_notification","auth_check","web_search","file_storage","iac_deploy",
    "ops_automation","cms_manage","data_api","site_monitor","observability",
    "apm_monitor","security_monitor","message_queue","message_broker","git_manage",
    "wiki_manage","document_system","file_share","paas_deploy","remote_desktop",
    "e_signature","smart_home","password_manager","data_table","lowcode",
    "etl_pipeline","mlops","llm_observability","api_test","spreadsheet",
    "rss_aggregator","email","flowchart","lowcode_platform","audio_transcribe","ai_testing",
    "send_sms"
]

missing = [n for n in expected if n not in names]
extra = names - set(expected)

print(f"\nExpected: {len(expected)}, Found: {len(t)}")
if missing:
    print(f"\nMISSING ({len(missing)}):")
    for n in missing:
        print(f"  ✗ {n}")
else:
    print("\n✅ ALL 86 tools registered!")
if extra:
    print(f"\nEXTRA ({len(extra)}): {sorted(extra)}")
