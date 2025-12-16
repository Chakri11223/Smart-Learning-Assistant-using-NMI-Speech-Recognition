import os

file_path = 'app.py'

with open(file_path, 'rb') as f:
    content = f.read()

# Marker for the end of the valid code
marker = b"if __name__ == '__main__':"
idx = content.find(marker)

if idx != -1:
    # Find the line with app.run
    run_marker = b"app.run(debug=True, host='0.0.0.0', port=5000)"
    run_idx = content.find(run_marker, idx)
    
    if run_idx != -1:
        # Find the end of that line
        end_of_line = content.find(b'\n', run_idx)
        if end_of_line == -1:
            end_of_line = len(content)
        
        # Keep content up to that point
        clean_content = content[:end_of_line+1]
        
        with open(file_path, 'wb') as f:
            f.write(clean_content)
        print("Successfully cleaned app.py")
    else:
        print("Could not find app.run call")
else:
    print("Could not find main block")
