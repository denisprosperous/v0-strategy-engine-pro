"""
InstitutionalSniperSignalGenerator: Entry/Exit Signal Logic
=============================================================
Combines smart money, DEX, and scam results to generate actionable alerts
Weights confidence, supports edit/override from user/telegram
"""
from typing import Dict, Any

class EntrySignal:
    def __init__(self, token_data, institutional_signal, scam_report, recommended_entry, confidence):
        self.token_data = token_data
        self.institutional_signal = institutional_signal
        self.scam_report = scam_report
        self.recommended_entry = recommended_entry
        self.confidence = confidence

class ExitSignal:
    def __init__(self, symbol, entry_price, current_price, pnl_percentage, reason, confidence, recommended_percentage):
        self.symbol = symbol
        self.entry_price = entry_price
        self.current_price = current_price
        self.pnl_percentage = pnl_percentage
        self.reason = reason
        self.confidence = confidence
        self.recommended_percentage = recommended_percentage

class InstitutionalSniperSignalGenerator:
    def __init__(self, risk_config):
        self.risk_config = risk_config
    def generate_entry_signal(self, token_data, inst_signal, scam_report) -> EntrySignal:
        score = inst_signal.confidence
        if scam_report['honeypot'] or not scam_report['owner_renounced']:
            score *= 0.2
        recommended_entry = {
            'amount': float(self.risk_config.max_position_size_pct),
            'stop_loss': float(token_data.liquidity_usd) * (1.0 - self.risk_config.hard_stop_loss_pct)
        }
        return EntrySignal(token_data, inst_signal, scam_report, recommended_entry, score)
    def generate_exit_signal(self, entry_signal, current_price, reason, distribution_alert=False) -> ExitSignal:
        pnl_perc = (current_price - entry_signal.recommended_entry['stop_loss']) / entry_signal.recommended_entry['stop_loss'] * 100
        confid = entry_signal.confidence
        perc = 0.5 if distribution_alert else 0.25
        return ExitSignal(entry_signal.token_data.symbol, entry_signal.recommended_entry['stop_loss'], current_price, pnl_perc, reason, confid, int(perc*100))
