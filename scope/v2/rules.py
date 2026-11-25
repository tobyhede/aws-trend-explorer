"""Conservative text-only alternative. Return a label and the matched phrase for inspection."""
import re

# Product-specific targets qualify an existing activity. A generic mention of 'support' does not.
TARGET = r'(?:ipv6|dual.stack|tls [\d.]+|(?:kubernetes|python|postgresql|mysql|apache kafka|node\.js) \d[\w.]*|(?:additional|more|new) (?:aws )?regions?|[a-z][\w-]* instance types?|(?:arm|graviton)\d? (?:processors?|instances?)|(?:nvidia|gpu) [\w-]+ instances?)'
SIGNALS = [
    ('extended', r'\b(?:support(?:s)?(?: for)?|available (?:in|on)|compatible with|across) (?:native |the |both )?'+TARGET),
    ('extended', r'\b(?:adds?|expands?|extends?) (?:[\w-]+ ){0,3}(?:region(?:al)? (?:support|availability)|support (?:for|to) (?:additional|more) )'),
    ('improved', r'\b(?:increases?|raises?|doubles?|reduces?|lowers?) (?:the |its |default |maximum |minimum |service |request |api |storage |throughput |payload |size |capacity |data |read |write ){0,6}(?:quota|limit|latency|cost|size|throughput|capacity)'),
    ('improved', r'\b(?:up to )?\d+(?:\.\d+)?(?:%|x) (?:faster|lower|higher|better|improvement|reduction)'),
    ('improved', r'\b(?:customiz(?:ation|able)|higher throughput|lower latency|fine[r-]+grained|performance improvements?|enhanced performance)\b'),
    ('new_capability', r'\b(?:integrates? (?:natively |directly )?with|new integration (?:with|between)|first.time support for|new (?:api|workflow|capability|feature) (?:that|to|for)|introduces? (?:a |an )?(?:new )?(?:api|feature|capability|integration)\b)'),
]
def predict(title,body):
    # Keep the primary claim ahead of downstream benefits, examples and boilerplate.
    opening = re.split(r'(?<=[.!?])\s+',body.strip(),maxsplit=2)
    for segment in [title,*opening[:2]]:
        for label,pattern in SIGNALS:
            hit=re.search(pattern,segment,re.I)
            if hit: return label,hit.group()
    return 'unclear','No specific change signal in the title or opening sentences'
