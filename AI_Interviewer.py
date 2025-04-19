import os
import time
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import HuggingFaceEndpoint
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

load_dotenv()

class AIInterviewer:
    def __init__(self):
        self.initialize_session()
        
        self.llm = HuggingFaceEndpoint(
            repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_length=2000,
            temperature=0.7,
            token=os.environ.get('HUGGINGFACEHUB_API_TOKEN')
        )

        self.question_generator_template = """
        You are an expert AI interviewer conducting a job interview for the position of {job_position}.
        
        Current interview stage: {stage}
        Candidate name: {name}
        Previous conversation: {chat_history}
        
        Resume information: {resume_info}
        
        Based on the current stage and information above, generate a relevant, professional interview question.
        
        If in introduction stage: Ask for candidate's name or job position they're applying for.
        If in general_questions stage: Ask about their background, motivation, and general qualifications.
        If in technical_questions stage: Ask specific questions relevant to the {job_position} role.
        If in experience_questions stage: Ask about their past experiences, referencing their resume information when possible.
        If in behavioral_questions stage: Ask about how they handled specific situations in the past.
        If in closing stage: Ask if they have questions or provide a conclusion to the interview.
        
        Generate only ONE question that's appropriate for the current stage. Make it conversational and engaging.
        """
        
        self.question_generator = PromptTemplate(
            input_variables=["job_position", "stage", "name", "chat_history", "resume_info"],
            template=self.question_generator_template
        )
        
        self.question_chain = LLMChain(
            llm=self.llm,
            prompt=self.question_generator,
            verbose=False
        )
    
    def initialize_session(self):
        """Initialize or reset the session state"""
        self.candidate_name = None
        self.job_position = None
        self.interview_stage = "introduction"
        self.last_question = ""
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.resume_entities = None
        print("\n[System] New interview session initialized\n")
    
    def set_resume_entities(self, resume_entities):
        """Set resume information extracted by the platform"""
        self.resume_entities = resume_entities
    
    def get_next_question(self):
        """Generate the next interview question based on current stage and context"""
        name = self.candidate_name if self.candidate_name else "Unknown"
        job_position = self.job_position if self.job_position else "the position"
        resume_info = str(self.resume_entities) if self.resume_entities else "No resume information available."
        
        chat_history = self.memory.load_memory_variables({})["chat_history"]
        chat_history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history]) if chat_history else ""
        
        if self.interview_stage == "introduction":
            if not self.candidate_name:
                self.last_question = "Hello! I'm your AI interviewer today. Could you please tell me your name?"
                return self.last_question
            elif not self.job_position:
                self.last_question = f"Nice to meet you, {self.candidate_name}! What position are you applying for?"
                return self.last_question
            else:
                self.interview_stage = "general_questions"
                self.last_question = f"Thank you, {self.candidate_name}. Let's begin the interview for the {self.job_position} position. Could you tell me a bit about yourself and your professional background?"
                return self.last_question
        
        response = self.question_chain.run(
            job_position=job_position,
            stage=self.interview_stage,
            name=name,
            chat_history=chat_history_str,
            resume_info=resume_info
        )
        
        self.last_question = response
        return response
    
    def advance_stage(self):
        """Move to the next interview stage"""
        stages = ["introduction", "general_questions", "technical_questions", 
                 "experience_questions", "behavioral_questions", "closing"]
        
        current_index = stages.index(self.interview_stage)
        if current_index < len(stages) - 1:
            self.interview_stage = stages[current_index + 1]
            print(f"\n[System] Moving to interview stage: {self.interview_stage}\n")
    
    def process_response(self, response):
        """Process candidate's response and update interview state"""
        self.memory.save_context(
            {"input": self.last_question},
            {"output": response}
        )
        
        if self.interview_stage == "introduction":
            if not self.candidate_name:
                self.candidate_name = response.strip()
                return self.get_next_question()
            elif not self.job_position:
                self.job_position = response.strip()
                return self.get_next_question()
        
        if self.interview_stage != "closing":
            should_advance_template = """
            Based on the interview conversation so far:
            {chat_history}
            
            Current stage: {stage}
            
            Should the interviewer move to the next stage of the interview? Consider:
            1. Have enough questions been asked in the current stage?
            2. Has the candidate provided sufficient information?
            3. Is it natural to transition to the next stage now?
            
            Respond with only "YES" or "NO".
            """
            
            should_advance_prompt = PromptTemplate(
                input_variables=["chat_history", "stage"],
                template=should_advance_template
            )
            
            chat_history = self.memory.load_memory_variables({})["chat_history"]
            chat_history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history]) if chat_history else ""
            
            should_advance_chain = LLMChain(llm=self.llm, prompt=should_advance_prompt)
            advance_decision = should_advance_chain.run(
                chat_history=chat_history_str,
                stage=self.interview_stage
            )
            
            if "YES" in advance_decision:
                self.advance_stage()
        
        return self.get_next_question()

def run_interview():
    print("\n" + "="*50)
    print("AI INTERVIEWER SYSTEM")
    print("="*50 + "\n")
    
    interviewer = AIInterviewer()
    
    sample_resume_info = {
        "skills": ["Python", "Data Analysis", "Machine Learning", "SQL", "Project Management"],
        "experience": [
            {"company": "TechCorp", "role": "Data Scientist", "duration": "2019-2022", 
             "highlights": ["Led a team of 3 analysts", "Improved model accuracy by 25%"]},
            {"company": "DataSystems", "role": "Analyst", "duration": "2017-2019", 
             "highlights": ["Developed ETL pipelines", "Automated reporting processes"]}
        ],
        "education": [
            {"degree": "M.S. Computer Science", "institution": "Tech University", "year": "2017"}
        ],
        "projects": ["Customer Segmentation Analysis", "Predictive Maintenance System"]
    }
    
    interviewer.set_resume_entities(sample_resume_info)
    
    interview_active = True
    
    while interview_active:
        question = interviewer.get_next_question()
        
        print("\n🤖 AI Interviewer:", end=" ")
        for char in question:
            print(char, end="", flush=True)
            time.sleep(0.01)
        print("\n")
        
        response = input("👤 You: ")
        
        if response.lower() == "/restart":
            interviewer.initialize_session()
            interviewer.set_resume_entities(sample_resume_info)
            continue
        elif response.lower() == "/exit":
            interview_active = False
            continue
    
        if "thank you for your time" in question.lower() or "interview is complete" in question.lower():
            interview_active = False
            new_interview = input("\nInterview completed. Start a new interview? (y/n): ")
            if new_interview.lower() == 'y':
                interviewer.initialize_session()
                interviewer.set_resume_entities(sample_resume_info)
                interview_active = True
                continue
        if interview_active:
            interviewer.process_response(response)
    
    print("\n")
    print("INTERVIEW COMPLETED")
    print("\n")
    print("Interview Summary:")
    print(f"Candidate: {interviewer.candidate_name}")
    print(f"Position: {interviewer.job_position}")
    print("\nInterview Transcript:")
    chat_history = interviewer.memory.load_memory_variables({})["chat_history"]
    for i, msg in enumerate(chat_history):
        if msg.type == "human":
            print(f"\n🤖 AI Interviewer: {msg.content}")
        else:
            print(f"👤 {interviewer.candidate_name}: {msg.content}")

if __name__ == "__main__":
    run_interview()
