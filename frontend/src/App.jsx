// Add this function to handle research button click
const handleResearchClick = () => {
  // Disable all input fields
  const inputFields = document.querySelectorAll('input');
  inputFields.forEach(input => {
    input.disabled = true;
  });
  
  // Start the research process
  startResearch();
}

// Then in your JSX, change the research button to use this handler:
<Button 
  onClick={handleResearchClick} 
  className="research-button"
>
  Research
</Button>

// When research completes, re-enable fields:
const researchComplete = () => {
  const inputFields = document.querySelectorAll('input');
  inputFields.forEach(input => {
    input.disabled = false;
  });
  
  // Other completion logic
}