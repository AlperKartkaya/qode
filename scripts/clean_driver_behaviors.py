import os
from datasets import load_dataset
from huggingface_hub import login

def clean_driver_behaviors():
    # Login using existing token
    token_path = os.path.expanduser("~/.cache/huggingface/token")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
        login(token=token)
    else:
        print("HF token not found!")
        return

    repo_id = "QoDe-5G/qode-driver-behaviors"
    print(f"Downloading dataset {repo_id}...")
    dataset = load_dataset(repo_id)
    
    print("Original dataset:")
    print(dataset)
    
    # Check the schema to find the label column and its values
    sample_split = list(dataset.keys())[0]
    features = dataset[sample_split].features
    
    label_field = None
    for field in ["label", "etiket", "class", "action", "sofor_eylemi"]:
        if field in features:
            label_field = field
            break
            
    if not label_field:
        print(f"Could not find label field. Features: {features}")
        return
        
    print(f"Using label field: {label_field}")
    
    # If the label is a ClassLabel, find the ID for smoking
    smoking_label_id = None
    if hasattr(features[label_field], "names"):
        names = features[label_field].names
        for i, name in enumerate(names):
            if "sigara" in name.lower() or "smoking" in name.lower():
                smoking_label_id = i
                print(f"Found smoking label: '{name}' (ID: {i})")
                break
                
    def filter_out_smoking(example):
        val = example[label_field]
        if isinstance(val, str):
            return "sigara" not in val.lower() and "smoking" not in val.lower()
        elif isinstance(val, int) and smoking_label_id is not None:
            return val != smoking_label_id
        return True

    print("Filtering out smoking labels...")
    cleaned_dataset = dataset.filter(filter_out_smoking)
    
    print("Cleaned dataset:")
    print(cleaned_dataset)
    
    print(f"Pushing cleaned dataset back to {repo_id}...")
    cleaned_dataset.push_to_hub(repo_id)
    print("Done!")

if __name__ == "__main__":
    clean_driver_behaviors()
