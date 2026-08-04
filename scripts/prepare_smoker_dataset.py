import os
import shutil
from datasets import load_dataset, Dataset, Features, Image, ClassLabel, concatenate_datasets
from huggingface_hub import login

def prepare_smoker_dataset():
    # Login
    token_path = os.path.expanduser("~/.cache/huggingface/token")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
        login(token=token)
    else:
        print("HF token not found!")
        return

    repo_id_new = "QoDe-5G/qode-smoker-detection"
    local_dir = os.path.expanduser("~/qode/data/datasets/smoker-detection")
    
    if not os.path.exists(local_dir):
        print(f"Error: Local directory {local_dir} not found. Did you extract the tar file?")
        return

    print("Loading local smoker-detection images...")
    
    try:
        # HuggingFace imagefolder automatically assigns labels based on directory names
        # Assuming folders are 'smoking' and 'not_smoking'
        local_dataset = load_dataset("imagefolder", data_dir=local_dir, split="train")
        print(f"Loaded {len(local_dataset)} images from local dataset.")
        print(f"Features: {local_dataset.features}")
    except Exception as e:
        print(f"Failed to load local dataset: {e}")
        return

    # Try to load qode-training-data to extract outdoor smoking instances
    print("Checking QoDe-5G/qode-training-data for extra images...")
    try:
        training_data = load_dataset("QoDe-5G/qode-training-data")
        sample_split = list(training_data.keys())[0]
        features = training_data[sample_split].features
        
        label_field = None
        for field in ["label", "etiket", "class", "action", "sofor_eylemi"]:
            if field in features:
                label_field = field
                break
                
        smoking_label_id = None
        if label_field and hasattr(features[label_field], "names"):
            for i, name in enumerate(features[label_field].names):
                if "sigara" in name.lower() or "smoking" in name.lower():
                    smoking_label_id = i
                    break
        
        if smoking_label_id is not None:
            print(f"Found smoking label in training-data: ID {smoking_label_id}")
            def filter_smoking(ex):
                return ex[label_field] == smoking_label_id
                
            outdoor_smoking = training_data[sample_split].filter(filter_smoking)
            print(f"Found {len(outdoor_smoking)} outdoor smoking images.")
            
            # Note: For this script, we will just push the local dataset to keep the feature schema clean.
            # Merging requires exact feature schema matches (image, label), which can be complex if original has more columns.
            print("Skipping automatic merge of outdoor images for now to preserve schema integrity.")
        else:
            print("No explicit smoking labels found in qode-training-data.")
    except Exception as e:
        print(f"Could not process qode-training-data: {e}")

    # Push to hub
    print(f"Pushing dataset to {repo_id_new}...")
    local_dataset.push_to_hub(repo_id_new)
    print("Done! Dataset is now organized on HuggingFace.")

if __name__ == "__main__":
    prepare_smoker_dataset()
