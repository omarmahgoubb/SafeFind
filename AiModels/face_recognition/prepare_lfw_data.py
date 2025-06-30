import os
import random
from collections import defaultdict
import numpy as np
import cv2

def prepare_lfw_pairs(lfw_base_path, output_dir, num_pairs_per_class=1000):

    print(f"Preparing LFW dataset from: {lfw_base_path}")
    print(f"Output directory for prepared data: {output_dir}")

    # Step 1: Map person IDs to their image paths
    person_images = defaultdict(list)
    lfw_images_path = os.path.join(lfw_base_path, 'lfw-deepfunneled')
    
    if not os.path.exists(lfw_images_path):
        print(f"Error: LFW images path not found: {lfw_images_path}")
        print("Please ensure 'lfw-deepfunneled' directory exists inside the provided lfw_base_path.")
        return

    for person_folder in os.listdir(lfw_images_path):
        person_path = os.path.join(lfw_images_path, person_folder)
        if os.path.isdir(person_path):
            for img_name in os.listdir(person_path):
                if img_name.lower().endswith((".jpg", ".png", ".jpeg")):
                    person_images[person_folder].append(os.path.join(person_path, img_name))

    all_person_ids = list(person_images.keys())
    print(f"Found {len(all_person_ids)} unique individuals in the dataset.")

    positive_pairs = []
    negative_pairs = []

    # Step 2: Generate Positive Pairs
    print("Generating positive pairs...")
    for person_id in all_person_ids:
        images_of_person = person_images[person_id]
        if len(images_of_person) >= 2:
            # Create all possible unique pairs for this person
            for i in range(len(images_of_person)):
                for j in range(i + 1, len(images_of_person)):
                    positive_pairs.append((images_of_person[i], images_of_person[j], 1))
    print(f"Generated {len(positive_pairs)} raw positive pairs.")

    # Step 3: Generate Negative Pairs
    print("Generating negative pairs...")
    num_negative_pairs_generated = 0
    while num_negative_pairs_generated < num_pairs_per_class:
        # Randomly pick two different persons
        person1_id, person2_id = random.sample(all_person_ids, 2)
        
        # Ensure both persons have images
        if not person_images[person1_id] or not person_images[person2_id]:
            continue

        # Randomly pick one image from each person
        img1_path = random.choice(person_images[person1_id])
        img2_path = random.choice(person_images[person2_id])
        
        negative_pairs.append((img1_path, img2_path, 0))
        num_negative_pairs_generated += 1
    print(f"Generated {len(negative_pairs)} negative pairs.")

    # Sample positive pairs to match the number of negative pairs, if positive pairs are abundant
    if len(positive_pairs) > num_pairs_per_class:
        positive_pairs = random.sample(positive_pairs, num_pairs_per_class)
    print(f"Using {len(positive_pairs)} positive pairs for final dataset.")

    # Combine all pairs
    all_pairs = positive_pairs + negative_pairs
    random.shuffle(all_pairs) # Shuffle to mix positive and negative pairs
    print(f"Total pairs generated: {len(all_pairs)}")

    # Save pairs to a file
    os.makedirs(output_dir, exist_ok=True)
    pairs_file = os.path.join(output_dir, 'lfw_pairs.txt')
    with open(pairs_file, 'w') as f:
        for img1, img2, label in all_pairs:
            f.write(f"{img1},{img2},{label}\n")
    print(f"Saved {len(all_pairs)} pairs to {pairs_file}")

    print("LFW dataset preparation complete.")

if __name__ == "__main__":
    # Define paths
    lfw_dataset_path = 'C:/Users/omara/Desktop/GradProject/lfw_dataset/'
    output_data_dir = 'C:/Users/omara/Desktop/GradProject/data/lfw_prepared'
    
    prepare_lfw_pairs(lfw_dataset_path, output_data_dir, num_pairs_per_class=5000) # Generate 5000 pairs of each type

